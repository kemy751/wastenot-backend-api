import uuid
from datetime import datetime
from app.extensions import db


class Seller(db.Model):
  
    __tablename__ = "seller"

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
        return f"<Seller {self.email}>"

    def to_dict(self):
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
