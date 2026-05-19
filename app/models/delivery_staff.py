"""
Seller profile model (previously Delivery staff).
"""

import uuid
from datetime import datetime
from app.extensions import db


class DeliveryStaff(db.Model):
    """
    Seller profile model. This was originally implemented as a delivery staff
    profile and retains the same fields to allow reuse of registration
    and verification flows for sellers who provide documents.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to User (one-to-one)
        email: Email address
        first_name: First name
        last_name: Last name
        phone: Phone number
        address: Optional address
        vehicle_type: Optional vehicle type (kept for compatibility)
        license_number: Optional license number (kept for compatibility)
        selfie_url: URL to selfie/photo
        national_id_front_url: URL to national ID front photo
        national_id_back_url: URL to national ID back photo
        is_verified: Verification status
        is_active: Active status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "delivery_staff"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=True)
    vehicle_type = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(100), unique=True, nullable=False)
    selfie_url = db.Column(db.String(500), nullable=False)
    national_id_front_url = db.Column(db.String(500), nullable=False)
    national_id_back_url = db.Column(db.String(500), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship("User", back_populates="delivery_staff")
    
    def __repr__(self):
        return f"<DeliveryStaff {self.email}>"
    
    def to_dict(self):
        """Convert delivery staff to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "address": self.address,
            "vehicle_type": self.vehicle_type,
            "license_number": self.license_number,
            "selfie_url": self.selfie_url,
            "national_id_front_url": self.national_id_front_url,
            "national_id_back_url": self.national_id_back_url,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
