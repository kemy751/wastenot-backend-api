import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import validates
from app.extensions import db

# --- ENUMS ---
class ElectronicType(enum.Enum):
    # Core Mobile & Computing
    SMARTPHONE = "SMARTPHONE"
    LAPTOP = "LAPTOP"
    TABLET = "TABLET"
    DESKTOP_PC = "DESKTOP_PC"
    MONITOR = "MONITOR"
    
    # Audio & Wearables
    AUDIO_HEADPHONES = "AUDIO_HEADPHONES"
    SPEAKERS_SUBWOOFERS = "SPEAKERS_SUBWOOFERS"
    SMART_WATCH = "SMART_WATCH"
    FITNESS_TRACKER = "FITNESS_TRACKER"
    
    # Entertainment & Gaming
    GAMING_CONSOLE = "GAMING_CONSOLE"
    TELEVISION = "TELEVISION"
    STREAMING_DEVICE = "STREAMING_DEVICE"  
    PROJECTOR = "PROJECTOR"
    
    # Automotive Electronics
    CAR_AUDIO_NAVIGATION = "CAR_AUDIO_NAVIGATION"
    
    # Cameras & Photography
    CAMERA_BODY = "CAMERA_BODY"
    CAMERA_LENS = "CAMERA_LENS"
    DRONE = "DRONE"
    
    # Computer Parts & Components
    GRAPHICS_CARD = "GRAPHICS_CARD"
    PROCESSOR_CPU = "PROCESSOR_CPU"
    MOTHERBOARD = "MOTHERBOARD"
    RAM_MEMORY = "RAM_MEMORY"
    STORAGE_SSD_HDD = "STORAGE_SSD_HDD"
    POWER_SUPPLY = "POWER_SUPPLY"
    
    # Networking Equipment
    ROUTER_MODEM = "ROUTER_MODEM"
    NETWORK_SWITCH = "NETWORK_SWITCH"
    
    # Smart Home & Peripherals
    SMART_HOME_HUB = "SMART_HOME_HUB"    
    SECURITY_CAMERA = "SECURITY_CAMERA"
    PRINTER_SCANNER = "PRINTER_SCANNER"
    KEYBOARD_MOUSE = "KEYBOARD_MOUSE"
    
    # Electronic Home Appliances & Tools
    HOME_APPLIANCES_TOOLS = "HOME_APPLIANCES_TOOLS" 
    
    # --- FIXED TYPO HERE ---
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


# --- MODELS ---
class Product(db.Model):
    __tablename__ = "products"

    # --- PRIMARY CORE COLUMNS ---
    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    brand = db.Column(db.String(100), nullable=False)
    model_name = db.Column(db.String(150), nullable=False)
    electronic_type = db.Column(db.Enum(ElectronicType), default=ElectronicType.OTHER, nullable=False)
    
    # --- METADATA INPUTS ---
    weight_kg = db.Column(db.Float, nullable=True, comment="Physical weight typed by user")
    release_year = db.Column(db.Integer, nullable=True, comment="Year device was originally released")
    has_lithium_battery = db.Column(db.Boolean, default=False, nullable=False)

    # --- THE COMPUTED STORAGE CACHE ---
    estimated_carbon_saved_kg = db.Column(db.Float, nullable=False, default=0.0)

    # --- RELATIONSHIPS (Cleaned backref conflict) ---
    listings = db.relationship('Listing', back_populates='product', lazy=True)


    # --- AUTOMATIC DATA LIFECYCLE RECALCULATOR ---
    @validates('brand', 'model_name', 'electronic_type', 'weight_kg', 'release_year', 'has_lithium_battery')
    def monitor_and_compute_impact(self, key, value):
        # 1. Update the property attribute value being processed instantly
        setattr(self, key, value)
        
        # 2. Prevent calculating on half-formed schemas before electronic_type is set
        if self.electronic_type:
            from app.services.green_sustainability import AdvancedGreenEngine
            self.estimated_carbon_saved_kg = AdvancedGreenEngine.calculate_product_impact(self)
            
        return value

    def __repr__(self):
        return f"<Product {self.brand} {self.model_name} ({self.electronic_type.value}) - EcoScore: {self.estimated_carbon_saved_kg}kg>"


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    seller_id = db.Column(db.Uuid, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Uuid, db.ForeignKey("products.id"), nullable=False)

    price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Using strict db.Enum mappings instead of vague strings keeps data squeaky clean
    condition = db.Column(db.Enum(ItemCondition), default=ItemCondition.USED, nullable=False)
    is_working = db.Column(db.Boolean, default=True, nullable=False)
    condition_notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(ListingStatus), default=ListingStatus.AVAILABLE, nullable=False)
    
    # Fixed deprecated utcnow to modern timezone-aware defaults
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Clear explicit relationship bindings
    product = db.relationship("Product", back_populates="listings")
    seller = db.relationship("User", backref=db.backref("listings", lazy=True))
    interests = db.relationship("ListingInterest", back_populates="listing", lazy=True)

    @property
    def interest_count(self):
        # Cleansed interest query referencing proper enum properties instead of string matches
        active_interests = [i for i in self.interests if i.status in [InterestStatus.EXPRESSED, InterestStatus.APPROVED]]
        return len(active_interests)


class ListingInterest(db.Model):
    __tablename__ = "listing_interests"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    listing_id = db.Column(db.Uuid, db.ForeignKey("listings.id"), nullable=False)
    buyer_id = db.Column(db.Uuid, db.ForeignKey("users.id"), nullable=False) 

    status = db.Column(db.Enum(InterestStatus), default=InterestStatus.EXPRESSED, nullable=False)
    message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    listing = db.relationship("Listing", back_populates="interests")
    buyer = db.relationship("User", backref=db.backref("expressed_interests", lazy=True))