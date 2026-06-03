import uuid
from datetime import datetime
from app.extensions import db

class SellerProfile(db.Model):
    __tablename__ = "seller_profiles"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    address = db.Column(db.Text, nullable=True)
    selfie_url = db.Column(db.String(500), nullable=False)
    national_id_front_url = db.Column(db.String(500), nullable=False)
    national_id_back_url = db.Column(db.String(500), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", back_populates="seller_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "address": self.address,
            "selfie_url": self.selfie_url,
            "national_id_front_url": self.national_id_front_url,
            "national_id_back_url": self.national_id_back_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }