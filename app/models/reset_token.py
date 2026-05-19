"""
Password reset token model.
"""

import uuid
from datetime import datetime
from app.extensions import db


class ResetToken(db.Model):
    """
    Password reset token model for password recovery flow.
    
    Attributes:
        id: UUID primary key
        token: The reset token string
        user_id: Foreign key to User
        expiry_date: Token expiration date
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "reset_tokens"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    expiry_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship("User", back_populates="reset_tokens")
    
    def __repr__(self):
        return f"<ResetToken {self.user_id}>"
    
    def is_valid(self):
        """Check if token is still valid (not expired)."""
        return datetime.utcnow() < self.expiry_date
