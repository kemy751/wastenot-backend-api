"""
Refresh token model for JWT token refresh mechanism.
"""

import uuid
from datetime import datetime, timedelta
from app.extensions import db


class RefreshToken(db.Model):
    """
    Refresh token model for JWT token refresh.
    
    Attributes:
        id: UUID primary key
        token: The refresh token string
        user_id: Foreign key to User
        expiry_date: Token expiration date
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "refresh_tokens"
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    expiry_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship("User", back_populates="refresh_tokens")
    
    def __repr__(self):
        return f"<RefreshToken {self.user_id}>"
    
    def is_valid(self):
        """Check if token is still valid (not expired)."""
        return datetime.utcnow() < self.expiry_date
