import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas import (
    SignupSchema,
    LoginSchema,
    ChangePasswordSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    RefreshTokenSchema,
    UpdateUserStatusSchema,
    RegisterSellerSchema,
)
from app.services import AuthService
from app.decorators import roles_required

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def error_response(message, status_code=400):
    return jsonify({"error": message, "status_code": status_code}), status_code


def success_response(message, data=None, status_code=200):
    response = {"message": message}
    if data:
        response["data"] = data
    return jsonify(response), status_code


@auth_bp.route("/register", methods=["POST"])
def register():

    try:
        # Get and validate request data
        schema = SignupSchema()
        data = schema.load(request.get_json())
        
        # Register user
        result, status_code = AuthService.signup(
            name=data.get("name"),
            email=data.get("email"),
            password=data.get("password"),
            role=data.get("role"),
            phone=data.get("phone"),
        )
        
        return jsonify({"message": "User registered successfully", "data": result}), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during registration: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except ValueError as e:
        logger.warning(f"Registration error: {str(e)}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        return error_response("Registration failed. Please try again.", 500)


@auth_bp.route("/register-seller", methods=["POST"])
def register_seller():
    try:
        # Get and validate request data
        schema = RegisterSellerSchema()
        data = schema.load(request.get_json())
        
        # Register delivery staff
        result, status_code = AuthService.register_seller(
            email=data.get("email"),
            password=data.get("password"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone=data.get("phone"),
            vehicle_type=data.get("vehicle_type"),
            license_number=data.get("license_number"),
            selfie_url=data.get("selfie_url"),
            national_id_front_url=data.get("national_id_front_url"),
            national_id_back_url=data.get("national_id_back_url"),
            address=data.get("address"),
        )
        
        return jsonify(result), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during delivery staff registration: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except ValueError as e:
        logger.warning(f"Delivery staff registration error: {str(e)}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"Unexpected error during delivery staff registration: {str(e)}")
        return error_response("Registration failed. Please try again.", 500)


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return tokens.
    
    Request body:
        {
            "email": "string",
            "password": "string"
        }
    """
    try:
        # Get and validate request data
        schema = LoginSchema()
        data = schema.load(request.get_json())
        
        # Authenticate user
        result, status_code = AuthService.login(
            email=data.get("email"),
            password=data.get("password"),
        )
        
        return jsonify(result), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during login: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except ValueError as e:
        error_msg = str(e)
        # Handle status code in error message (hack for now)
        if len(e.args) > 1:
            return error_response(error_msg, e.args[1])
        return error_response(error_msg, 401)
    
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        return error_response("Login failed. Please try again.", 500)


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """
    Refresh JWT tokens.
    
    Request body:
        {
            "refresh_token": "string"
        }
    """
    try:
        # Get and validate request data
        schema = RefreshTokenSchema()
        data = schema.load(request.get_json())
        
        # Get user ID from JWT (should be present since this is being called by client)
        user_id = get_jwt_identity()
        
        if not user_id:
            return error_response("Unauthorized", 401)
        
        # Refresh tokens
        result, status_code = AuthService.refresh_tokens(
            refresh_token_string=data.get("refresh_token"),
            user_id=user_id,
        )
        
        return jsonify(result), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during token refresh: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except ValueError as e:
        logger.warning(f"Token refresh error: {str(e)}")
        return error_response(str(e), 401)
    
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}")
        return error_response("Token refresh failed. Please try again.", 500)


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """
    Get current user profile.
    Requires valid JWT token.
    """
    try:
        user_id = get_jwt_identity()
        result, status_code = AuthService.get_profile(user_id)
        return jsonify(result), status_code
    
    except ValueError as e:
        logger.warning(f"Profile retrieval error: {str(e)}")
        return error_response(str(e), 404)
    
    except Exception as e:
        logger.error(f"Unexpected error during profile retrieval: {str(e)}")
        return error_response("Profile retrieval failed. Please try again.", 500)


@auth_bp.route("/change-password", methods=["PUT"])
@jwt_required()
def change_password():
    """
    Change user password.
    Requires valid JWT token.
    
    Request body:
        {
            "old_password": "string",
            "new_password": "string"
        }
    """
    try:
        # Get and validate request data
        schema = ChangePasswordSchema()
        data = schema.load(request.get_json())
        
        user_id = get_jwt_identity()
        
        # Change password
        result, status_code = AuthService.change_password(
            user_id=user_id,
            old_password=data.get("old_password"),
            new_password=data.get("new_password"),
        )
        
        return jsonify(result), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during password change: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except ValueError as e:
        logger.warning(f"Password change error: {str(e)}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"Unexpected error during password change: {str(e)}")
        return error_response("Password change failed. Please try again.", 500)


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Request password reset.
    Sends reset email (if account exists).
    
    Request body:
        {
            "email": "string"
        }
    """
    try:
        # Get and validate request data
        schema = ForgotPasswordSchema()
        data = schema.load(request.get_json())
        
        # Request password reset
        result, status_code = AuthService.forgot_password(
            email=data.get("email")
        )
        
        return jsonify(result), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during forgot password: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except Exception as e:
        logger.error(f"Unexpected error during forgot password: {str(e)}")
        return error_response("Password reset request failed. Please try again.", 500)


@auth_bp.route("/reset-password", methods=["PUT"])
def reset_password():
    """
    Reset password using reset token.
    
    Request body:
        {
            "reset_token": "string",
            "new_password": "string"
        }
    """
    try:
        # Get and validate request data
        schema = ResetPasswordSchema()
        data = schema.load(request.get_json())
        
        # Reset password
        result, status_code = AuthService.reset_password(
            reset_token=data.get("reset_token"),
            new_password=data.get("new_password"),
        )
        
        return jsonify(result), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during password reset: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except ValueError as e:
        logger.warning(f"Password reset error: {str(e)}")
        return error_response(str(e), 400)
    
    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}")
        return error_response("Password reset failed. Please try again.", 500)


@auth_bp.route("/pending-users", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_pending_users():
    """
    Get all pending users (admin only).
    Requires valid JWT token and admin role.
    """
    try:
        result, status_code = AuthService.get_pending_users()
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"Unexpected error retrieving pending users: {str(e)}")
        return error_response("Failed to retrieve pending users.", 500)


@auth_bp.route("/all-users", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_all_users():
    """
    Get all users (admin only).
    Requires valid JWT token and admin role.
    """
    try:
        result, status_code = AuthService.get_all_users()
        return jsonify(result), status_code
    
    except Exception as e:
        logger.error(f"Unexpected error retrieving all users: {str(e)}")
        return error_response("Failed to retrieve all users.", 500)


@auth_bp.route("/update-status", methods=["PUT"])
@jwt_required()
@roles_required("admin")
def update_user_status():
    """
    Update user status (admin only).
    Requires valid JWT token and admin role.
    
    Request body:
        {
            "email": "string",
            "status": "string"
        }
    """
    try:
        # Get and validate request data
        schema = UpdateUserStatusSchema()
        data = schema.load(request.get_json())
        
        user_id = get_jwt_identity()
        
        # Update user status
        result, status_code = AuthService.update_user_status(
            admin_user_id=user_id,
            email=data.get("email"),
            new_status=data.get("status"),
        )
        
        return jsonify(result), status_code
    
    except ValidationError as e:
        logger.warning(f"Validation error during user status update: {e.messages}")
        return error_response(f"Validation error: {str(e.messages)}", 400)
    
    except ValueError as e:
        logger.warning(f"User status update error: {str(e)}")
        return error_response(str(e), 403 if "admin" in str(e).lower() else 400)
    
    except Exception as e:
        logger.error(f"Unexpected error during user status update: {str(e)}")
        return error_response("Failed to update user status.", 500)


@auth_bp.route("/users-by-role/<role>", methods=["GET"])
@jwt_required()
@roles_required("admin")
def get_users_by_role(role):
    """
    Get all users with a specific role (admin only).
    Requires valid JWT token and admin role.
    
    URL Parameters:
        role: The role to filter by
    """
    try:
        user_id = get_jwt_identity()
        result, status_code = AuthService.get_users_by_role(
            admin_user_id=user_id,
            role=role,
        )
        return jsonify(result), status_code
    
    except ValueError as e:
        logger.warning(f"Get users by role error: {str(e)}")
        return error_response(str(e), 403)
    
    except Exception as e:
        logger.error(f"Unexpected error getting users by role: {str(e)}")
        return error_response("Failed to retrieve users by role.", 500)
