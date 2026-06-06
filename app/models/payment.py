# app/models/payment.py
import enum
import uuid
from datetime import datetime, timezone, timedelta
from app.extensions import db


class PaymentStatus(enum.Enum):
    PENDING   = "PENDING"    # created, awaiting mock confirmation
    HELD      = "HELD"       # paid, in 7-day admin escrow
    RELEASED  = "RELEASED"   # escrow released, seller paid
    REFUNDED  = "REFUNDED"   # disputed and refunded to buyer
    CANCELLED = "CANCELLED"  # payment abandoned


class DisputeStatus(enum.Enum):
    OPEN     = "OPEN"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class Payment(db.Model):
    __tablename__ = "payments"

    id                  = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id          = db.Column(db.String(36), db.ForeignKey("listings.id"), nullable=False)
    buyer_id            = db.Column(db.String(36), db.ForeignKey("users.id"),    nullable=False)
    seller_id           = db.Column(db.String(36), db.ForeignKey("users.id"),    nullable=False)
    interest_id         = db.Column(db.String(36), db.ForeignKey("listing_interests.id"), nullable=False)

    amount              = db.Column(db.Numeric(12, 2), nullable=False)
    status              = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    # Mock transaction reference — replaced by real gateway ref in future
    transaction_ref     = db.Column(db.String(100), nullable=True)

    # Escrow window — 7 days from payment confirmation
    escrow_release_date = db.Column(db.DateTime, nullable=True)

    # Pickup proof photo uploaded by buyer at QR scan
    pickup_photo_url    = db.Column(db.String(500), nullable=True)

    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                    onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    listing  = db.relationship("Listing",  foreign_keys=[listing_id])
    buyer    = db.relationship("User",     foreign_keys=[buyer_id])
    seller   = db.relationship("User",     foreign_keys=[seller_id])
    interest = db.relationship("ListingInterest", foreign_keys=[interest_id])
    disputes = db.relationship("PaymentDispute", back_populates="payment",
                                cascade="all, delete-orphan")

    def to_dict(self):
        # Get the most recent dispute if any
        latest_dispute = self.disputes[-1] if self.disputes else None
        return {
            "id":                  self.id,
            "listing_id":          self.listing_id,
            "buyer_id":            self.buyer_id,
            "seller_id":           self.seller_id,
            "interest_id":         self.interest_id,
            "amount":              str(self.amount),
            "status":              self.status.value,
            "transaction_ref":     self.transaction_ref,
            "escrow_release_date": self.escrow_release_date.isoformat() if self.escrow_release_date else None,
            "pickup_photo_url":    self.pickup_photo_url,
            "created_at":          self.created_at.isoformat(),
            "updated_at":          self.updated_at.isoformat(),
            "listing_title":       (
                f"{self.listing.product.brand} {self.listing.product.model_name}"
                if self.listing and self.listing.product else "Device"
            ),
            "seller_name":         self.seller.name if self.seller else None,
            "buyer_name":          self.buyer.name  if self.buyer  else None,
            "dispute":             latest_dispute.to_dict() if latest_dispute else None,
        }


class PaymentDispute(db.Model):
    __tablename__ = "payment_disputes"

    id         = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = db.Column(db.String(36), db.ForeignKey("payments.id"), nullable=False)
    buyer_id   = db.Column(db.String(36), db.ForeignKey("users.id"),    nullable=False)

    reason     = db.Column(db.Text, nullable=False)
    status     = db.Column(db.Enum(DisputeStatus), default=DisputeStatus.OPEN, nullable=False)
    resolution = db.Column(db.Text, nullable=True)  # admin notes

    raised_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at= db.Column(db.DateTime, nullable=True)

    payment    = db.relationship("Payment", back_populates="disputes")
    buyer      = db.relationship("User", foreign_keys=[buyer_id])

    def to_dict(self):
        return {
            "id":          self.id,
            "payment_id":  self.payment_id,
            "buyer_id":    self.buyer_id,
            "reason":      self.reason,
            "status":      self.status.value,
            "resolution":  self.resolution,
            "raised_at":   self.raised_at.isoformat(),
            "created_at":  self.raised_at.isoformat(),  # alias for frontend consistency
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }