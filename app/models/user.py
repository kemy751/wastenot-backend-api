import uuid
from datetime import datetime
from enum import Enum
from app.extensions import db


class UserRole(Enum):
    ADMIN = "admin"
    SELLER = "seller"
    BUYER = "buyer"


class UserStatus(Enum):
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
    role = db.Column(
        db.String(50),
        default=UserRole.BUYER.value,
        nullable=False
    )
    status = db.Column(
        db.String(50),
        default=UserStatus.PENDING_APPROVAL.value,
        nullable=False
    )
    phone = db.Column(db.String(20), nullable=True)
    is_email_verified = db.Column(db.Boolean, default=False)
    district = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    refresh_tokens = db.relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    reset_tokens = db.relationship("ResetToken", back_populates="user", cascade="all, delete-orphan")
    delivery_staff = db.relationship("Seller", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.email}>"
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "phone": self.phone,
            "is_email_verified": self.is_email_verified,
            "district": self.district,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
