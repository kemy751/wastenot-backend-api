# app/routes/payment_routes.py
import os
import uuid
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.payment_service import PaymentService
from app.decorators import roles_required
from app.models.user import UserRole

logger = logging.getLogger(__name__)
payment_bp = Blueprint("payment", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def _save_photo(file) -> str:
    """Save pickup proof photo and return relative URL."""
    ext = file.filename.rsplit(".", 1)[-1].lower()
    name = f"pickup_{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config.get("UPLOAD_FOLDER", "uploads"), "pickups")
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, name))
    return f"/uploads/pickups/{name}"


# ── POST /payments  — buyer initiates payment after QR scan ──────────────────
@payment_bp.route("/payments", methods=["POST"])
@jwt_required()
@roles_required(UserRole.BUYER)
def create_payment():
    """
    Body (multipart/form-data):
      interest_id     — UUID of the approved ListingInterest
      pickup_photo    — image file (required — proof of physical collection)
    """
    interest_id = request.form.get("interest_id") or (request.get_json() or {}).get("interest_id")
    if not interest_id:
        return jsonify({"error": "interest_id is required"}), 400

    # Handle optional photo upload
    pickup_photo_url = None
    photo = request.files.get("pickup_photo")
    if photo and photo.filename:
        ext = photo.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": "Photo must be png, jpg, jpeg, or webp"}), 400
        try:
            pickup_photo_url = _save_photo(photo)
        except Exception as e:
            logger.error(f"Photo upload failed: {e}")
            return jsonify({"error": "Photo upload failed"}), 500

    buyer_id = get_jwt_identity()
    try:
        payment = PaymentService.create(
            interest_id=interest_id,
            buyer_id=buyer_id,
            pickup_photo_url=pickup_photo_url,
        )
        return jsonify({
            "message": "Payment confirmed. Funds held in escrow for 7 days.",
            "data": payment.to_dict(),
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("Unexpected error creating payment")
        return jsonify({"error": "Payment failed. Please try again."}), 500


# ── GET /payments/:id ─────────────────────────────────────────────────────────
@payment_bp.route("/payments/<payment_id>", methods=["GET"])
@jwt_required()
def get_payment(payment_id):
    try:
        payment = PaymentService.get_by_id(payment_id)
        user_id = get_jwt_identity()
        # Only buyer, seller, or admin can view
        if payment.buyer_id != user_id and payment.seller_id != user_id:
            from app.models.user import User
            from app.extensions import db
            user = db.session.get(User, user_id)
            if not user or user.role != "admin":
                return jsonify({"error": "Access denied"}), 403
        return jsonify({"data": payment.to_dict()}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


# ── GET /me/payments  — buyer's payment history ───────────────────────────────
@payment_bp.route("/me/payments", methods=["GET"])
@jwt_required()
def get_my_payments():
    buyer_id = get_jwt_identity()
    payments = PaymentService.get_buyer_payments(buyer_id)
    return jsonify([p.to_dict() for p in payments]), 200


# ── GET /me/seller-payments  — seller's received payments ────────────────────
@payment_bp.route("/me/seller-payments", methods=["GET"])
@jwt_required()
@roles_required(UserRole.SELLER)
def get_seller_payments():
    seller_id = get_jwt_identity()
    payments = PaymentService.get_seller_payments(seller_id)
    return jsonify([p.to_dict() for p in payments]), 200


# ── POST /payments/:id/release  — admin releases escrow ──────────────────────
@payment_bp.route("/payments/<payment_id>/release", methods=["POST"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def release_payment(payment_id):
    admin_id = get_jwt_identity()
    try:
        payment = PaymentService.release(payment_id, admin_id)
        return jsonify({
            "message": "Payment released to seller.",
            "data": payment.to_dict(),
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── POST /payments/:id/dispute  — buyer raises dispute ───────────────────────
@payment_bp.route("/payments/<payment_id>/dispute", methods=["POST"])
@jwt_required()
@roles_required(UserRole.BUYER)
def raise_dispute(payment_id):
    buyer_id = get_jwt_identity()
    body = request.get_json() or {}
    reason = body.get("reason", "").strip()
    if not reason:
        return jsonify({"error": "reason is required"}), 400
    try:
        dispute = PaymentService.raise_dispute(payment_id, buyer_id, reason)
        return jsonify({
            "message": "Dispute raised. Admin will review within 48 hours.",
            "data": dispute.to_dict(),
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── POST /payments/disputes/:id/resolve  — admin resolves dispute ─────────────
@payment_bp.route("/payments/disputes/<dispute_id>/resolve", methods=["POST"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def resolve_dispute(dispute_id):
    admin_id = get_jwt_identity()
    body     = request.get_json() or {}
    action     = body.get("action")      # 'refund' | 'reject'
    resolution = body.get("resolution", "").strip()

    if action not in ("refund", "reject"):
        return jsonify({"error": "action must be 'refund' or 'reject'"}), 400
    if not resolution:
        return jsonify({"error": "resolution note is required"}), 400

    try:
        dispute = PaymentService.resolve_dispute(dispute_id, admin_id, action, resolution)
        return jsonify({
            "message": f"Dispute {dispute.status.value.lower()}.",
            "data": dispute.to_dict(),
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── GET /admin/payments  — all platform payments ──────────────────────────────
@payment_bp.route("/admin/payments", methods=["GET"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def get_all_payments():
    payments = PaymentService.get_all()
    return jsonify([p.to_dict() for p in payments]), 200
