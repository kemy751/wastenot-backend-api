import os
import uuid
import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from werkzeug.utils import secure_filename
from app.schemas import (
    SignupSchema,
    LoginSchema,
    ChangePasswordSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    RefreshTokenSchema,
    UpdateUserStatusSchema,
    UpdateProfileSchema,
)
from app.services import AuthService
from app.decorators import roles_required

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ---------------------------------------------------------------------------
# File upload config
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
KYC_UPLOAD_FOLDER = os.environ.get("KYC_UPLOAD_FOLDER", "uploads/kyc")


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _save_file(file, subfolder: str) -> str:
    """
    Save an uploaded FileStorage object to disk and return the public URL path.

    Swap this function out for a Cloudinary / S3 upload if needed — the rest
    of the route stays the same.
    """
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(KYC_UPLOAD_FOLDER, subfolder)
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, unique_name)
    file.save(save_path)
    # Return as a URL path the frontend / storage layer can access
    return f"/{save_path}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def error_response(message, status_code=400):
    return jsonify({"error": message, "status_code": status_code}), status_code


def success_response(message, data=None, status_code=200):
    response = {"message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@auth_bp.route("/auth/register", methods=["POST"])
def register():
    """Register a regular buyer/admin user."""
    try:
        data = SignupSchema().load(request.get_json())

        result, status_code = AuthService.signup(
            name=data["name"],
            email=data["email"],
            password=data["password"],
            role=data.get("role"),
            phone=data.get("phone"),
        )

        return success_response("User registered successfully", result, status_code)

    except ValidationError as e:
        logger.warning(f"Validation error during registration: {e.messages}")
        return error_response(e.messages, 422)

    except ValueError as e:
        logger.warning(f"Registration error: {e}")
        return error_response(str(e), 400)

    except Exception as e:
        logger.exception("Unexpected error during registration")
        return error_response("Registration failed. Please try again.", 500)


@auth_bp.route("/auth/register-seller", methods=["POST"])
def register_seller():
    """
    Register a seller (creates User + SellerProfile in one step).
    Expects multipart/form-data with fields:
        name, email, password, phone, address (optional)
        and files: selfie, national_id_front, national_id_back
    """
    try:
        # Remove trailing commas that created tuples
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")
        address = request.form.get("address")

        # Validation
        if not all([name, email, password, phone]):
            return error_response("name, email, password, phone are required", 422)

        # File uploads
        file_fields = {
            "selfie": "selfie_url",
            "national_id_front": "national_id_front_url",
            "national_id_back": "national_id_back_url",
        }
        file_urls = {}

        for form_key, service_key in file_fields.items():
            file = request.files.get(form_key)
            if not file or file.filename == "":
                return error_response(f"{form_key} image is required", 422)
            if not _allowed_file(file.filename):
                return error_response(
                    f"{form_key} must be a valid image (png, jpg, jpeg, webp)", 422
                )
            file_urls[service_key] = _save_file(file, subfolder=form_key)

        # Call service
        result, status_code = AuthService.register_seller(
            name=name,
            email=email,
            password=password,
            phone=phone,
            address=address,
            selfie_url=file_urls["selfie_url"],
            national_id_front_url=file_urls["national_id_front_url"],
            national_id_back_url=file_urls["national_id_back_url"],
        )

        return jsonify(result), status_code

    except ValueError as e:
        logger.warning(f"Seller registration error: {e}")
        return error_response(str(e), 400)

    except Exception as e:
        logger.exception("Unexpected error during seller registration")
        return error_response("Registration failed. Please try again.", 500)


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    """Authenticate a user and return access + refresh tokens."""
    try:
        data = LoginSchema().load(request.get_json())

        result, status_code = AuthService.login(
            email=data["email"],
            password=data["password"],
        )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error during login: {e.messages}")
        return error_response(e.messages, 422)

    except ValueError as e:
        status = e.args[1] if len(e.args) > 1 else 401
        return error_response(str(e), status)

    except Exception as e:
        logger.exception("Unexpected error during login")
        return error_response("Login failed. Please try again.", 500)


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Send a password-reset email (always returns 200 to avoid user enumeration)."""
    try:
        data = ForgotPasswordSchema().load(request.get_json())
        result, status_code = AuthService.forgot_password(email=data["email"])
        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error during forgot password: {e.messages}")
        return error_response(e.messages, 422)

    except Exception as e:
        logger.exception("Unexpected error during forgot password")
        return error_response("Password reset request failed. Please try again.", 500)


@auth_bp.route("/reset-password", methods=["PUT"])
def reset_password():
    """Reset a password using a valid reset token."""
    try:
        data = ResetPasswordSchema().load(request.get_json())

        result, status_code = AuthService.reset_password(
            reset_token=data["reset_token"],
            new_password=data["new_password"],
        )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error during password reset: {e.messages}")
        return error_response(e.messages, 422)

    except ValueError as e:
        logger.warning(f"Password reset error: {e}")
        return error_response(str(e), 400)

    except Exception as e:
        logger.exception("Unexpected error during password reset")
        return error_response("Password reset failed. Please try again.", 500)


# ---------------------------------------------------------------------------
# Authenticated routes (any role)
# ---------------------------------------------------------------------------

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Exchange a valid refresh token for a new access + refresh token pair."""
    try:
        data = RefreshTokenSchema().load(request.get_json())
        user_id = get_jwt_identity()

        result, status_code = AuthService.refresh_tokens(
            refresh_token_string=data["refresh_token"],
            user_id=user_id,
        )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error during token refresh: {e.messages}")
        return error_response(e.messages, 422)

    except ValueError as e:
        logger.warning(f"Token refresh error: {e}")
        return error_response(str(e), 401)

    except Exception as e:
        logger.exception("Unexpected error during token refresh")
        return error_response("Token refresh failed. Please try again.", 500)


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Return the authenticated user's profile (includes seller_profile if applicable)."""
    try:
        user_id = get_jwt_identity()
        result, status_code = AuthService.get_profile(user_id)
        return jsonify(result), status_code

    except ValueError as e:
        logger.warning(f"Profile retrieval error: {e}")
        return error_response(str(e), 404)

    except Exception as e:
        logger.exception("Unexpected error during profile retrieval")
        return error_response("Profile retrieval failed. Please try again.", 500)


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    """Update the authenticated user's basic profile fields."""
    try:
        data = UpdateProfileSchema().load(request.get_json())
        user_id = get_jwt_identity()

        result, status_code = AuthService.update_profile(
            user_id=user_id,
            **data,
        )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error during profile update: {e.messages}")
        return error_response(e.messages, 422)

    except ValueError as e:
        logger.warning(f"Profile update error: {e}")
        return error_response(str(e), 400)

    except Exception as e:
        logger.exception("Unexpected error during profile update")
        return error_response("Profile update failed. Please try again.", 500)


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    """Change password for the authenticated user."""
    try:
        data = ChangePasswordSchema().load(request.get_json())
        user_id = get_jwt_identity()

        result, status_code = AuthService.change_password(
            user_id=user_id,
            old_password=data["old_password"],
            new_password=data["new_password"],
        )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error during password change: {e.messages}")
        return error_response(e.messages, 422)

    except ValueError as e:
        logger.warning(f"Password change error: {e}")
        return error_response(str(e), 400)

    except Exception as e:
        logger.exception("Unexpected error during password change")
        return error_response("Password change failed. Please try again.", 500)


# ---------------------------------------------------------------------------
# Admin-only routes
# ---------------------------------------------------------------------------

@auth_bp.route("/users", methods=["GET", "OPTIONS"])
@jwt_required()
@roles_required("admin")
def get_all_users():
    """Return all users (admin only)."""
    try:
        result, status_code = AuthService.get_all_users()
        return jsonify(result), status_code

    except Exception as e:
        logger.exception("Unexpected error retrieving all users")
        return error_response("Failed to retrieve users.", 500)


@auth_bp.route("/users/pending", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_pending_users():
    """Return users with PENDING_APPROVAL status (admin only)."""
    
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
            
    try:
        result, status_code = AuthService.get_pending_users()
        return jsonify(result), status_code

    except Exception as e:
        logger.exception("Unexpected error retrieving pending users")
        return error_response("Failed to retrieve pending users.", 500)


@auth_bp.route("/users/role/<role>", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_users_by_role(role):
    """Return all users with a given role (admin only)."""
    
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    
    try:
        admin_id = get_jwt_identity()
        result, status_code = AuthService.get_users_by_role(admin_user_id=admin_id, role=role)
        return jsonify(result), status_code

    except ValueError as e:
        logger.warning(f"Get users by role error: {e}")
        return error_response(str(e), 400)

    except Exception as e:
        logger.exception("Unexpected error getting users by role")
        return error_response("Failed to retrieve users by role.", 500)


@auth_bp.route("/users/status", methods=["PUT"])
@jwt_required()
@roles_required("admin")
def update_user_status():
    """Update a user's status (admin only)."""
    try:
        data = UpdateUserStatusSchema().load(request.get_json())
        admin_id = get_jwt_identity()

        result, status_code = AuthService.update_user_status(
            admin_user_id=admin_id,
            email=data["email"],
            new_status=data["status"],
        )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error during status update: {e.messages}")
        return error_response(e.messages, 422)

    except ValueError as e:
        logger.warning(f"Status update error: {e}")
        status = 403 if "admin" in str(e).lower() else 400
        return error_response(str(e), status)

    except Exception as e:
        logger.exception("Unexpected error during user status update")
        return error_response("Failed to update user status.", 500)


@auth_bp.route("/sellers/<seller_profile_id>/verify", methods=["PUT", "OPTIONS"])
@jwt_required()
@roles_required("admin")
def verify_seller(seller_profile_id):
    """
    Approve or reject a seller's KYC documents (admin only).

    Request body:
        {
            "action": "approve" | "reject",
            "reason": "string"   // required when action is reject
        }
    """

    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    
    try:
        body = request.get_json() or {}
        action = body.get("action")
        reason = body.get("reason")

        if action not in ("approve", "reject"):
            return error_response("action must be 'approve' or 'reject'", 400)

        if action == "reject" and not reason:
            return error_response("reason is required when rejecting a seller", 400)

        admin_id = get_jwt_identity()
        result, status_code = AuthService.verify_seller(
            admin_user_id=admin_id,
            seller_profile_id=seller_profile_id,
            action=action,
            reason=reason,
        )

        return jsonify(result), status_code

    except ValueError as e:
        logger.warning(f"Seller verification error: {e}")
        return error_response(str(e), 400)

    except Exception as e:
        logger.exception("Unexpected error during seller verification")
        return error_response("Seller verification failed. Please try again.", 500)