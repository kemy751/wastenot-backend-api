import uuid
from datetime import datetime, timezone
from app.extensions import db

class ListingImage(db.Model):
    __tablename__ = "listing_images"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = db.Column(db.String(36), db.ForeignKey("listings.id"), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    listing = db.relationship("Listing", back_populates="images")