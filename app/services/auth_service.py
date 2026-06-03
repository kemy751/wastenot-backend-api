"""
Authentication service containing all business logic.
"""

import secrets
import logging
from datetime import datetime, timedelta
from flask import current_app
from flask_jwt_extended import create_access_token
from bcrypt import hashpw, gensalt, checkpw
from app.extensions import db
from app.models import User, UserRole, UserStatus, RefreshToken, ResetToken, SellerProfile
from app.events.signals import (
    user_registered,
    password_reset_requested,
    user_status_updated,
    seller_registered
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt."""
        bcrypt_rounds = current_app.config.get("BCRYPT_LOG_ROUNDS", 10)
        salt = gensalt(rounds=bcrypt_rounds)
        hashed = hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    
    @staticmethod
    def verify_password(stored_hash, password):
        """Verify password against bcrypt hash."""
        return checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    
    @staticmethod
    def signup(name, email, password, role=None, phone=None):
        """Register a new user (buyer or admin)."""
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            raise ValueError("Email already registered", 400)
        
        if not role:
            role = UserRole.BUYER.value

        if role == UserRole.SELLER.value:
            status = UserStatus.PENDING_APPROVAL.value
        else:
            status = UserStatus.ACTIVE.value
        
        hashed_password = AuthService.hash_password(password)
        
        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role=role,
            status=status,
            phone=phone,
        )
        
        db.session.add(user)
        db.session.commit()
        
        user_registered.send(current_app._get_current_object(), user=user)
        logger.info(f"User registered: {email}")
        
        return {
            "userId": user.id,
            "email": user.email,
            "role": user.role,
            "status": user.status,
        }, 201
    
    @staticmethod
    def register_seller(
        name, email, password, phone, selfie_url,
        national_id_front_url, national_id_back_url, address
    ):

        # Check existing email
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already registered")
        
        hashed = AuthService.hash_password(password)

        user = User(
            name=name,
            email=email,
            password=hashed,
            role=UserRole.SELLER.value,
            status=UserStatus.PENDING_APPROVAL.value,
            phone=phone,
        )
        db.session.add(user)
        db.session.flush()  # get user.id
        
        # Create SellerProfile (without license_number)
        seller_profile = SellerProfile(
            user_id=user.id,
            selfie_url=selfie_url,
            national_id_front_url=national_id_front_url,
            national_id_back_url=national_id_back_url,
            address=address,
        )
        db.session.add(seller_profile)
        db.session.commit()
        seller_registered.send(current_app._get_current_object(), user=user, seller_profile=seller_profile)
        logger.info(f"Seller registered: {email}")
        
        return {
            "message": "Seller registration pending review",
            "userId": user.id,
            "status": "pending_approval",
        }, 201
    
    @staticmethod
    def login(email, password):
        """Authenticate user and generate tokens."""
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("Invalid email or password")
        
        if not AuthService.verify_password(user.password, password):
            raise ValueError("Invalid email or password")
        
        # Check user status
        if user.status == UserStatus.SUSPENDED.value:
            raise ValueError("Your account has been suspended. Please contact support.")
        if user.status == UserStatus.INACTIVE.value:
            raise ValueError("Your account is inactive. Please contact support.")
        if user.status == UserStatus.PENDING_APPROVAL.value:
            raise ValueError("Your account is pending approval. Please wait for notification.")
        
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role}
        )
        
        refresh_token_string = secrets.token_urlsafe(64)
        expiry_date = datetime.utcnow() + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
        
        refresh_token = RefreshToken(
            token=refresh_token_string,
            user_id=user.id,
            expiry_date=expiry_date,
        )
        db.session.add(refresh_token)
        db.session.commit()
        
        logger.info(f"User logged in: {email}")
        
        return {
            "message": "Login successful",
            "data": {
                "accessToken": access_token,
                "refreshToken": refresh_token_string,
                "userId": user.id,
                "role": user.role,
                "status": user.status,
            },
        }, 200

    @staticmethod
    def change_password(user_id, old_password, new_password):
        """Change user password."""
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found", 404)
        
        if not AuthService.verify_password(user.password, old_password):
            raise ValueError("Current password is incorrect", 400)
        
        user.password = AuthService.hash_password(new_password)
        RefreshToken.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        return {"message": "Password changed successfully"}, 200
    
    @staticmethod
    def forgot_password(email):
        """Request password reset (send email with reset link)."""
        user = User.query.filter_by(email=email).first()
        if user:
            try:
                reset_token = secrets.token_urlsafe(64)
                expiry_date = datetime.utcnow() + timedelta(
                    seconds=current_app.config["RESET_TOKEN_EXPIRY"]
                )
                token_record = ResetToken(
                    token=reset_token,
                    user_id=user.id,
                    expiry_date=expiry_date,
                )
                db.session.add(token_record)
                db.session.commit()
                
                reset_link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={reset_token}"
                password_reset_requested.send(
                    current_app._get_current_object(),
                    user=user,
                    reset_link=reset_link
                )
                logger.info(f"Password reset requested for: {email}")
            except Exception as e:
                logger.error(f"Error processing password reset for {email}: {str(e)}")
        
        return {
            "message": "If an account exists with that email, a password reset link has been sent."
        }, 200
    
    @staticmethod
    def reset_password(reset_token, new_password):
        """Reset user password using reset token."""
        token_record = ResetToken.query.filter_by(token=reset_token).first()
        if not token_record:
            raise ValueError("Invalid or expired reset token")
        
        if not token_record.is_valid():
            db.session.delete(token_record)
            db.session.commit()
            raise ValueError("Reset token has expired")
        
        user = token_record.user
        user.password = AuthService.hash_password(new_password)
        RefreshToken.query.filter_by(user_id=user.id).delete()
        db.session.delete(token_record)
        db.session.commit()
        
        logger.info(f"Password reset completed for: {user.email}")
        return {"message": "Password reset successful"}, 200
    
    @staticmethod
    def refresh_tokens(refresh_token_string, user_id):
        """Refresh JWT tokens."""
        refresh_token = RefreshToken.query.filter_by(
            token=refresh_token_string,
            user_id=user_id
        ).first()
        
        if not refresh_token:
            raise ValueError("Invalid refresh token")
        
        if not refresh_token.is_valid():
            db.session.delete(refresh_token)
            db.session.commit()
            raise ValueError("Refresh token has expired")
        
        user = refresh_token.user
        new_access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role}
        )
        
        new_refresh_token_string = secrets.token_urlsafe(64)
        new_expiry_date = datetime.utcnow() + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
        
        db.session.delete(refresh_token)
        new_refresh_token = RefreshToken(
            token=new_refresh_token_string,
            user_id=user.id,
            expiry_date=new_expiry_date,
        )
        db.session.add(new_refresh_token)
        db.session.commit()
        
        logger.info(f"Tokens refreshed for user: {user.email}")
        return {
            "message": "Tokens refreshed successfully",
            "data": {
                "accessToken": new_access_token,
                "refreshToken": new_refresh_token_string,
            },
        }, 200
    
    @staticmethod
    def get_profile(user_id):
        """Get user profile information."""
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        return {
            "message": "Profile retrieved successfully",
            "data": user.to_dict(),
        }, 200
    
    @staticmethod
    def get_pending_users():
        """Get all users pending approval."""
        pending_users = User.query.filter_by(
            status=UserStatus.PENDING_APPROVAL.value
        ).all()
        users_data = [user.to_dict() for user in pending_users]
        return {
            "message": "Pending users retrieved successfully",
            "data": users_data,
        }, 200
    
    @staticmethod
    def get_all_users():
        """Get all users."""
        users = User.query.all()
        users_data = [user.to_dict() for user in users]
        return {
            "message": "All users retrieved successfully",
            "data": users_data,
        }, 200
    
    @staticmethod
    def update_user_status(admin_user_id, email, new_status):
        """Update user status (admin only)."""
        admin_user = db.session.get(User, admin_user_id)
        if not admin_user or admin_user.role != UserRole.ADMIN.value:
            raise ValueError("Only admin can update user status")
        
        user = User.query.filter_by(email=email).first()
        if not user:
            raise ValueError("User not found")
        
        old_status = user.status
        user.status = new_status
        db.session.commit()
        
        user_status_updated.send(
            current_app._get_current_object(),
            user=user,
            old_status=old_status,
            new_status=new_status,
        )
        
        logger.info(f"User status updated: {email} ({old_status} -> {new_status})")
        return {
            "message": f"User status updated to {new_status}",
            "data": user.to_dict(),
        }, 200
    
    @staticmethod
    def get_users_by_role(admin_user_id, role):
        """Get all users with a specific role (admin only)."""
        admin_user = db.session.get(User, admin_user_id)
        if not admin_user or admin_user.role != UserRole.ADMIN.value:
            raise ValueError("Only admin can retrieve users by role")
        
        users = User.query.filter_by(role=role).all()
        users_data = [user.to_dict() for user in users]
        return {
            "message": f"Users with role '{role}' retrieved successfully",
            "data": users_data,
        }, 200
    
    @staticmethod
    def verify_seller(admin_user_id, seller_profile_id, action, reason=None):

        admin = db.session.get(User, admin_user_id)
        if not admin or admin.role != UserRole.ADMIN.value:
            raise ValueError("Only admin can verify sellers")
        
        seller_profile = db.session.get(SellerProfile, seller_profile_id)
        if not seller_profile:
            raise ValueError("Seller profile not found")
        
        user = seller_profile.user
        if user.role != UserRole.SELLER.value:
            raise ValueError("User is not a seller")
        
        if action == "approve":
            user.status = UserStatus.ACTIVE.value
            user.verification_reason = None
            message = "Seller approved successfully"
        elif action == "reject":
            user.status = UserStatus.SUSPENDED.value
            user.verification_reason = reason or "No reason provided"
            message = "Seller rejected"
        else:
            raise ValueError("Invalid action, must be 'approve' or 'reject'")
        
        db.session.commit()
        logger.info(f"Seller {user.email} verification: {action}")
        return {"message": message}, 200