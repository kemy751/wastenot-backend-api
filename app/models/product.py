import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import validates
from app.extensions import db
from .listing_image import ListingImage

# --- ENUMS (Kept as is) ---
class ElectronicType(enum.Enum):
    SMARTPHONE = "SMARTPHONE"
    LAPTOP = "LAPTOP"
    TABLET = "TABLET"
    DESKTOP_PC = "DESKTOP_PC"
    MONITOR = "MONITOR"
    AUDIO_HEADPHONES = "AUDIO_HEADPHONES"
    SPEAKERS_SUBWOOFERS = "SPEAKERS_SUBWOOFERS"
    SMART_WATCH = "SMART_WATCH"
    FITNESS_TRACKER = "FITNESS_TRACKER"
    GAMING_CONSOLE = "GAMING_CONSOLE"
    TELEVISION = "TELEVISION"
    STREAMING_DEVICE = "STREAMING_DEVICE"
    PROJECTOR = "PROJECTOR"
    CAR_AUDIO_NAVIGATION = "CAR_AUDIO_NAVIGATION"
    CAMERA_BODY = "CAMERA_BODY"
    CAMERA_LENS = "CAMERA_LENS"
    DRONE = "DRONE"
    GRAPHICS_CARD = "GRAPHICS_CARD"
    PROCESSOR_CPU = "PROCESSOR_CPU"
    MOTHERBOARD = "MOTHERBOARD"
    RAM_MEMORY = "RAM_MEMORY"
    STORAGE_SSD_HDD = "STORAGE_SSD_HDD"
    POWER_SUPPLY = "POWER_SUPPLY"
    ROUTER_MODEM = "ROUTER_MODEM"
    NETWORK_SWITCH = "NETWORK_SWITCH"
    SMART_HOME_HUB = "SMART_HOME_HUB"
    SECURITY_CAMERA = "SECURITY_CAMERA"
    PRINTER_SCANNER = "PRINTER_SCANNER"
    KEYBOARD_MOUSE = "KEYBOARD_MOUSE"
    HOME_APPLIANCES_TOOLS = "HOME_APPLIANCES_TOOLS"
    OTHER = "OTHER"

class ItemCondition(enum.Enum):
    NEW = "NEW"
    OPEN_BOX = "OPEN_BOX"
    USED = "USED"
    FOR_PARTS = "FOR_PARTS"

class ListingStatus(enum.Enum):
    AVAILABLE = "AVAILABLE"
    PENDING_SALE = "PENDING_SALE"
    SOLD = "SOLD"
    UNLISTED = "UNLISTED" 

class InterestStatus(enum.Enum):
    EXPRESSED = "EXPRESSED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# --- MODELS (Standardized to String(36)) ---

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand = db.Column(db.String(100), nullable=False)
    model_name = db.Column(db.String(150), nullable=False)
    seller_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    electronic_type = db.Column(db.Enum(ElectronicType), default=ElectronicType.OTHER, nullable=False)
    weight_kg = db.Column(db.Float, nullable=True)
    release_year = db.Column(db.Integer, nullable=True)
    has_lithium_battery = db.Column(db.Boolean, default=False, nullable=False)
    estimated_carbon_saved_kg = db.Column(db.Float, nullable=False, default=0.0)

    listings = db.relationship('Listing', back_populates='product', lazy=True)

    @validates('brand', 'model_name', 'electronic_type', 'weight_kg', 'release_year', 'has_lithium_battery')
    def monitor_and_compute_impact(self, key, value):
        self.__dict__[key] = value
        if self.electronic_type:
            from app.services.green_sustainability import AdvancedGreenEngine
            self.estimated_carbon_saved_kg = AdvancedGreenEngine.calculate_product_impact(self)
        return value

class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id"), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    condition = db.Column(db.Enum(ItemCondition), default=ItemCondition.USED, nullable=False)
    is_working = db.Column(db.Boolean, default=True, nullable=False)
    condition_notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(ListingStatus), default=ListingStatus.AVAILABLE, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    product = db.relationship("Product", back_populates="listings")
    seller = db.relationship("User", back_populates="listings")
    interests = db.relationship("ListingInterest", back_populates="listing", lazy=True)

    images = db.relationship("ListingImage", back_populates="listing",
        cascade="all, delete-orphan", order_by="ListingImage.sort_order")
    
class ListingInterest(db.Model):
    __tablename__ = "listing_interests"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = db.Column(db.String(36), db.ForeignKey("listings.id"), nullable=False)
    buyer_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum(InterestStatus), default=InterestStatus.EXPRESSED, nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    listing = db.relationship("Listing", back_populates="interests")
    buyer = db.relationship("User", back_populates="expressed_interests")