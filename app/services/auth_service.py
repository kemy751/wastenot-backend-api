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
from app.models import User, UserRole, UserStatus, RefreshToken, ResetToken, Seller
from app.events.signals import (
    user_registered,
    password_reset_requested,
    user_status_updated,
    delivery_staff_registered,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""
    
    @staticmethod
    def hash_password(password):
        """
        Hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        bcrypt_rounds = current_app.config.get("BCRYPT_LOG_ROUNDS", 10)
        salt = gensalt(rounds=bcrypt_rounds)
        hashed = hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    
    @staticmethod
    def verify_password(stored_hash, password):
        """
        Verify password against bcrypt hash.
        
        Args:
            stored_hash: Stored hashed password
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    
    @staticmethod
    def signup(name, email, password, role=None, phone=None):
        """
        Register a new user.
        
        Args:
            name: User's full name
            email: User's email address
            password: Plain text password
            role: User role (optional, defaults to buyer)
            phone: User's phone number (optional)
            
        Returns:
            Tuple of (user_dict, status_code)
            
        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Set default role
        if not role:
            role = UserRole.BUYER.value

        # Determine initial status based on role: sellers require approval
        if role == UserRole.SELLER.value:
            status = UserStatus.PENDING_APPROVAL.value
        else:
            status = UserStatus.ACTIVE.value
        
        # Hash password
        hashed_password = AuthService.hash_password(password)
        
        # Create new user
        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role=role,
            status=status,
            phone=phone,
        )
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
        # Emit signal after successful save
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
        email, password, first_name, last_name, phone,
        vehicle_type, license_number, selfie_url,
        national_id_front_url, national_id_back_url, address=None
    ):
        """
        Register a new delivery staff member.
        
        Args:
            email: Staff email
            password: Plain text password
            first_name: First name
            last_name: Last name
            phone: Phone number
            vehicle_type: Vehicle type
            license_number: Driver license number
            selfie_url: URL to selfie
            national_id_front_url: URL to national ID front
            national_id_back_url: URL to national ID back
            address: Optional address
            
        Returns:
            Tuple of (response_dict, status_code)
            
        Raises:
            ValueError: If email or license already exists
        """
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        # Check if license number already exists
        existing_staff = Seller.query.filter_by(license_number=license_number).first()
        if existing_staff:
            raise ValueError("License number already registered")
        
        # Hash password
        hashed_password = AuthService.hash_password(password)
        
        # Create user with seller role and pending approval status
        user = User(
            name=f"{first_name} {last_name}",
            email=email,
            password=hashed_password,
            role=UserRole.SELLER.value,
            status=UserStatus.PENDING_APPROVAL.value,
            phone=phone,
        )
        
        # Save user first
        db.session.add(user)
        db.session.flush()  # Flush to get user ID without committing
        
        # Create seller record (reuses delivery_staff table)
        seller = Seller(
            user_id=user.id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            vehicle_type=vehicle_type,
            license_number=license_number,
            selfie_url=selfie_url,
            national_id_front_url=national_id_front_url,
            national_id_back_url=national_id_back_url,
            address=address,
        )

        db.session.add(seller)
        db.session.commit()

        # Emit signal after successful save (payload key kept for compatibility)
        delivery_staff_registered.send(
            current_app._get_current_object(),
            user=user,
            delivery_staff=seller
        )

        logger.info(f"Seller registered: {email}")

        return {
            "message": "Seller registration pending review",
            "userId": user.id,
            "status": "pending_review",
        }, 201
    
    @staticmethod
    def login(email, password):
        """
        Authenticate user and generate tokens.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Tuple of (response_dict, status_code)
            
        Raises:
            ValueError: If credentials invalid or account issue
        """
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            raise ValueError("Invalid email or password")
        
        # Check user status (suspended → inactive → pending_approval)
        if user.status == UserStatus.SUSPENDED.value:
            raise ValueError("Your account has been suspended. Please contact support.", 403)
        
        if user.status == UserStatus.INACTIVE.value:
            raise ValueError("Your account is inactive. Please contact support.", 403)
        
        if user.status == UserStatus.PENDING_APPROVAL.value:
            raise ValueError("Your account is pending approval. Please wait for notification.", 403)
        
        # Verify password
        if not AuthService.verify_password(user.password, password):
            raise ValueError("Invalid email or password")
        
        # Generate JWT access token
        access_token = create_access_token(identity=user.id)
        
        # Generate and store refresh token
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
        """
        Change user password.
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            Tuple of (message_dict, status_code)
            
        Raises:
            ValueError: If old password incorrect
        """
        user = db.session.get(User, user_id)
        
        if not user:
            raise ValueError("User not found")
        
        # Verify old password
        if not AuthService.verify_password(user.password, old_password):
            raise ValueError("Current password is incorrect")
        
        # Hash and save new password
        user.password = AuthService.hash_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        
        return {"message": "Password changed successfully"}, 200
    
    @staticmethod
    def forgot_password(email):
        """
        Request password reset (send email with reset link).
        
        Args:
            email: User email
            
        Returns:
            Tuple of (message_dict, status_code)
            
        Note:
            Returns same message regardless of whether email exists (security).
        """
        # Find user silently (don't reveal if email exists)
        user = User.query.filter_by(email=email).first()
        
        if user:
            try:
                # Generate reset token
                reset_token = secrets.token_urlsafe(64)
                expiry_date = datetime.utcnow() + timedelta(
                    seconds=current_app.config["RESET_TOKEN_EXPIRY"]
                )
                
                # Save reset token
                token_record = ResetToken(
                    token=reset_token,
                    user_id=user.id,
                    expiry_date=expiry_date,
                )
                
                db.session.add(token_record)
                db.session.commit()
                
                # Build reset link
                reset_link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={reset_token}"
                
                # Emit signal (will send email in listener)
                password_reset_requested.send(
                    current_app._get_current_object(),
                    user=user,
                    reset_link=reset_link
                )
                
                logger.info(f"Password reset requested for: {email}")
            except Exception as e:
                logger.error(f"Error processing password reset for {email}: {str(e)}")
        
        # Always return same message for security
        return {
            "message": "If an account exists with that email, a password reset link has been sent."
        }, 200
    
    @staticmethod
    def reset_password(reset_token, new_password):
        """
        Reset user password using reset token.
        
        Args:
            reset_token: Reset token from email
            new_password: New password
            
        Returns:
            Tuple of (message_dict, status_code)
            
        Raises:
            ValueError: If token invalid or expired
        """
        # Find token
        token_record = ResetToken.query.filter_by(token=reset_token).first()
        
        if not token_record:
            raise ValueError("Invalid or expired reset token")
        
        # Check if token is expired
        if not token_record.is_valid():
            db.session.delete(token_record)
            db.session.commit()
            raise ValueError("Reset token has expired")
        
        # Get user
        user = token_record.user
        
        # Update password
        user.password = AuthService.hash_password(new_password)
        
        # Delete token after use
        db.session.delete(token_record)
        db.session.commit()
        
        logger.info(f"Password reset completed for: {user.email}")
        
        return {"message": "Password reset successful"}, 200
    
    @staticmethod
    def refresh_tokens(refresh_token_string, user_id):
        """
        Refresh JWT tokens.
        
        Args:
            refresh_token_string: Refresh token from request
            user_id: User ID from JWT
            
        Returns:
            Tuple of (response_dict, status_code)
            
        Raises:
            ValueError: If token invalid or expired
        """
        # Find refresh token
        refresh_token = RefreshToken.query.filter_by(
            token=refresh_token_string,
            user_id=user_id
        ).first()
        
        if not refresh_token:
            raise ValueError("Invalid refresh token")
        
        # Check if token is expired
        if not refresh_token.is_valid():
            db.session.delete(refresh_token)
            db.session.commit()
            raise ValueError("Refresh token has expired")
        
        # Get user
        user = refresh_token.user
        
        # Generate new access token
        new_access_token = create_access_token(identity=user.id)
        
        # Generate new refresh token
        new_refresh_token_string = secrets.token_urlsafe(64)
        new_expiry_date = datetime.utcnow() + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
        
        # Create new refresh token and delete old one
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
        """
        Get user profile information.
        
        Args:
            user_id: User ID
            
        Returns:
            Tuple of (response_dict, status_code)
            
        Raises:
            ValueError: If user not found
        """
        user = db.session.get(User, user_id)
        
        if not user:
            raise ValueError("User not found")
        
        return {
            "message": "Profile retrieved successfully",
            "data": user.to_dict(),
        }, 200
    
    @staticmethod
    def get_pending_users():
        """
        Get all users pending approval.
        
        Returns:
            Tuple of (response_dict, status_code)
        """
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
        """
        Get all users.
        
        Returns:
            Tuple of (response_dict, status_code)
        """
        users = User.query.all()
        users_data = [user.to_dict() for user in users]
        
        return {
            "message": "All users retrieved successfully",
            "data": users_data,
        }, 200
    
    @staticmethod
    def update_user_status(admin_user_id, email, new_status):
        """
        Update user status (admin only).
        
        Args:
            admin_user_id: Admin user ID
            email: Email of user to update
            new_status: New status
            
        Returns:
            Tuple of (response_dict, status_code)
            
        Raises:
            ValueError: If user not found or admin not authorized
        """
        # Verify requesting user is admin by querying DB
        admin_user = db.session.get(User, admin_user_id)
        
        if not admin_user or admin_user.role != UserRole.ADMIN.value:
            raise ValueError("Only admin can update user status")
        
        # Find user to update
        user = User.query.filter_by(email=email).first()
        
        if not user:
            raise ValueError("User not found")
        
        old_status = user.status
        user.status = new_status
        db.session.commit()
        
        # Emit signal after successful save
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
        """
        Get all users with a specific role (admin only).
        
        Args:
            admin_user_id: Admin user ID
            role: Role to filter by
            
        Returns:
            Tuple of (response_dict, status_code)
            
        Raises:
            ValueError: If admin not authorized
        """
        # Verify requesting user is admin by querying DB
        admin_user = db.session.get(User, admin_user_id)
        
        if not admin_user or admin_user.role != UserRole.ADMIN.value:
            raise ValueError("Only admin can retrieve users by role")
        
        # Get users with specified role
        users = User.query.filter_by(role=role).all()
        users_data = [user.to_dict() for user in users]
        
        return {
            "message": f"Users with role '{role}' retrieved successfully",
            "data": users_data,
        }, 200
