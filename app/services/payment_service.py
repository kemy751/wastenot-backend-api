# app/services/payment_service.py
import uuid
import logging
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models.payment import Payment, PaymentStatus, PaymentDispute, DisputeStatus
from app.models.product import Listing, ListingInterest, ListingStatus, InterestStatus
from app.models.user import User

logger = logging.getLogger(__name__)

ESCROW_DAYS = 7  # days before funds auto-release to seller


class PaymentService:

    # ── Create payment (mock — no real gateway yet) ───────────────────────────
    @staticmethod
    def create(interest_id: str, buyer_id: str, pickup_photo_url: str = None) -> Payment:
        """
        Called after QR scan verified + photo taken.
        Creates Payment in HELD status immediately (mock gateway = instant success).
        Atomically updates:
          - Interest → COMPLETED
          - Listing  → SOLD (escrow period begins)
        """
        interest = db.session.get(ListingInterest, interest_id)
        if not interest:
            raise ValueError("Interest record not found")
        if interest.buyer_id != buyer_id:
            raise ValueError("You are not the buyer for this interest")
        if interest.status != InterestStatus.APPROVED:
            raise ValueError("Payment can only be made for an approved interest")

        listing = db.session.get(Listing, interest.listing_id)
        if not listing:
            raise ValueError("Listing not found")
        if listing.status != ListingStatus.PENDING_SALE:
            raise ValueError(f"Listing is not in PENDING_SALE status (current: {listing.status.value})")

        # Check no duplicate payment
        existing = Payment.query.filter_by(
            interest_id=interest_id,
            buyer_id=buyer_id,
        ).filter(Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.HELD])).first()
        if existing:
            raise ValueError("A payment for this interest already exists")

        try:
            escrow_release = datetime.now(timezone.utc) + timedelta(days=ESCROW_DAYS)

            payment = Payment(
                listing_id          = listing.id,
                buyer_id            = buyer_id,
                seller_id           = listing.seller_id,
                interest_id         = interest_id,
                amount              = listing.price,
                status              = PaymentStatus.HELD,   # mock: instantly held
                transaction_ref     = f"MOCK-{uuid.uuid4().hex[:12].upper()}",
                escrow_release_date = escrow_release,
                pickup_photo_url    = pickup_photo_url,
            )

            # Store pickup photo on interest too
            if pickup_photo_url:
                interest.pickup_photo_url = pickup_photo_url

            # Transition statuses atomically
            interest.status = InterestStatus.COMPLETED
            listing.status  = ListingStatus.SOLD

            db.session.add(payment)
            db.session.commit()

            logger.info(f"Payment {payment.id} created for listing {listing.id} by buyer {buyer_id}")
            return payment

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create payment: {e}")
            raise

    # ── Get payment by ID ────────────────────────────────────────────────────
    @staticmethod
    def get_by_id(payment_id: str) -> Payment:
        payment = db.session.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        return payment

    # ── Get payment by interest ──────────────────────────────────────────────
    @staticmethod
    def get_by_interest(interest_id: str) -> Payment:
        return Payment.query.filter_by(interest_id=interest_id).first()

    # ── Get all payments for a buyer ─────────────────────────────────────────
    @staticmethod
    def get_buyer_payments(buyer_id: str):
        return Payment.query.filter_by(buyer_id=buyer_id)\
                            .order_by(Payment.created_at.desc()).all()

    # ── Get all payments for a seller ────────────────────────────────────────
    @staticmethod
    def get_seller_payments(seller_id: str):
        return Payment.query.filter_by(seller_id=seller_id)\
                            .order_by(Payment.created_at.desc()).all()

    # ── Get all payments (admin) ─────────────────────────────────────────────
    @staticmethod
    def get_all():
        return Payment.query.order_by(Payment.created_at.desc()).all()

    # ── Release escrow (admin or auto after 7 days) ──────────────────────────
    @staticmethod
    def release(payment_id: str, admin_user_id: str) -> Payment:
        payment = db.session.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        if payment.status != PaymentStatus.HELD:
            raise ValueError(f"Cannot release payment with status: {payment.status.value}")

        # Verify admin
        admin = db.session.get(User, admin_user_id)
        if not admin or admin.role != "admin":
            raise ValueError("Only admin can release payments")

        try:
            payment.status = PaymentStatus.RELEASED
            db.session.commit()
            logger.info(f"Payment {payment_id} released by admin {admin_user_id}")
            return payment
        except Exception as e:
            db.session.rollback()
            raise

    # ── Raise dispute (buyer, within 7-day window) ───────────────────────────
    @staticmethod
    def raise_dispute(payment_id: str, buyer_id: str, reason: str) -> PaymentDispute:
        payment = db.session.get(Payment, payment_id)
        if not payment:
            raise ValueError("Payment not found")
        if payment.buyer_id != buyer_id:
            raise ValueError("You are not the buyer for this payment")
        if payment.status != PaymentStatus.HELD:
            raise ValueError("Disputes can only be raised on payments in escrow (HELD)")

        # Check within 7-day window
        now = datetime.now(timezone.utc)
        if payment.escrow_release_date and now > payment.escrow_release_date:
            raise ValueError("The 7-day dispute window has closed for this payment")

        # No duplicate open disputes
        existing = PaymentDispute.query.filter_by(
            payment_id=payment_id,
            status=DisputeStatus.OPEN
        ).first()
        if existing:
            raise ValueError("A dispute is already open for this payment")

        try:
            dispute = PaymentDispute(
                payment_id=payment_id,
                buyer_id=buyer_id,
                reason=reason,
            )
            db.session.add(dispute)
            db.session.commit()
            logger.info(f"Dispute raised on payment {payment_id} by buyer {buyer_id}")
            return dispute
        except Exception as e:
            db.session.rollback()
            raise

    # ── Resolve dispute (admin) ──────────────────────────────────────────────
    @staticmethod
    def resolve_dispute(dispute_id: str, admin_user_id: str, action: str, resolution: str) -> PaymentDispute:
        """action: 'refund' | 'reject'"""
        admin = db.session.get(User, admin_user_id)
        if not admin or admin.role != "admin":
            raise ValueError("Only admin can resolve disputes")

        dispute = db.session.get(PaymentDispute, dispute_id)
        if not dispute:
            raise ValueError("Dispute not found")
        if dispute.status != DisputeStatus.OPEN:
            raise ValueError("Dispute is already resolved")

        try:
            dispute.resolution  = resolution
            dispute.resolved_at = datetime.now(timezone.utc)

            if action == "refund":
                dispute.status          = DisputeStatus.RESOLVED
                dispute.payment.status  = PaymentStatus.REFUNDED
                # Revert listing to AVAILABLE so it can be relisted
                dispute.payment.listing.status = ListingStatus.AVAILABLE
                # Revert interest
                if dispute.payment.interest:
                    dispute.payment.interest.status = InterestStatus.CANCELLED
            elif action == "reject":
                dispute.status = DisputeStatus.REJECTED
                # Payment stays HELD — admin will release separately
            else:
                raise ValueError("action must be 'refund' or 'reject'")

            db.session.commit()
            return dispute
        except Exception as e:
            db.session.rollback()
            raise

    # ── Auto-release expired escrows (call from cron / scheduled task) ───────
    @staticmethod
    def auto_release_expired():
        """Release all HELD payments where escrow_release_date has passed."""
        now = datetime.now(timezone.utc)
        expired = Payment.query.filter(
            Payment.status == PaymentStatus.HELD,
            Payment.escrow_release_date <= now,
        ).all()

        released = []
        for payment in expired:
            try:
                payment.status = PaymentStatus.RELEASED
                released.append(payment.id)
            except Exception as e:
                logger.error(f"Failed to auto-release payment {payment.id}: {e}")

        if released:
            db.session.commit()
            logger.info(f"Auto-released {len(released)} payments: {released}")

        return released
