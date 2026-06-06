import uuid
from datetime import datetime
from enum import Enum
from app.extensions import db

class UserRole(str, Enum):
    BUYER = "buyer"
    SELLER = "seller"
    ADMIN = "admin"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=UserRole.BUYER.value, nullable=False)
    status = db.Column(db.String(50), default=UserStatus.ACTIVE.value, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    verification_reason = db.Column(db.Text, nullable=True)   # for admin rejection

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seller_profile = db.relationship("SellerProfile", back_populates="user", uselist=False)
    refresh_tokens = db.relationship("RefreshToken", back_populates="user", lazy=True)
    reset_tokens = db.relationship("ResetToken", back_populates="user", lazy=True)
    listings = db.relationship("Listing", back_populates="seller", lazy=True)
    expressed_interests = db.relationship("ListingInterest", back_populates="buyer", lazy=True)

    def to_dict(self):
        sp = self.seller_profile
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "phone": self.phone,
            "verification_reason": self.verification_reason,
            "created_at": self.created_at.isoformat(),
            "seller_profile_id": sp.id if sp else None,
            "seller_profile": {
                "id":                    sp.id,
                "address":               sp.address if hasattr(sp, "address") else None,
                "selfie_url":            sp.selfie_url if hasattr(sp, "selfie_url") else None,
                "national_id_front_url": sp.national_id_front_url if hasattr(sp, "national_id_front_url") else None,
                "national_id_back_url":  sp.national_id_back_url if hasattr(sp, "national_id_back_url") else None,
            } if sp else None,
        }