"""
Signal listeners for the application event system.
Handles business logic triggered by events (emails, logging, etc.).
"""

import logging
from app.events.signals import (
    user_registered,
    password_reset_requested,
    user_status_updated,
    delivery_staff_registered,
    seller_registered,
)
from app.services.mail_service import MailService

logger = logging.getLogger(__name__)


def register_event_listeners():
    """
    Register all event listeners.
    Called during app initialization.
    """
    
    @user_registered.connect
    def on_user_registered(sender, user, **kwargs):
        """Handle user registration event."""
        logger.info(f"User registered: {user.email}")
        try:
            mail_service = MailService()
            mail_service.send_welcome_email(
                user.name,
                user.email,
                user.role,
                user.status,
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
    
    @password_reset_requested.connect
    def on_password_reset_requested(sender, user, reset_link, **kwargs):
        """Handle password reset request event."""
        logger.info(f"Password reset requested for: {user.email}")
        try:
            mail_service = MailService()
            mail_service.send_password_reset_email(
                user.name,
                user.email,
                reset_link,
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
    
    @seller_registered.connect
    def on_seller_registered(sender, user, delivery_staff, **kwargs):
        """Handle seller registration event (delivery_staff payload kept for compatibility)."""
        logger.info(f"Seller registered: {user.email}")
        try:
            mail_service = MailService()
            # Send confirmation email to seller
            mail_service.send_seller_confirmation_email(
                delivery_staff.first_name,
                delivery_staff.email,
            )
            # Send notification to admin
            mail_service.send_seller_registration_admin_email(
                delivery_staff.first_name,
                delivery_staff.last_name,
                delivery_staff.email,
                delivery_staff.phone,
                delivery_staff.vehicle_type,
                delivery_staff.license_number,
                delivery_staff.selfie_url,
                delivery_staff.national_id_front_url,
                delivery_staff.national_id_back_url,
            )
        except Exception as e:
            logger.error(f"Failed to send seller emails for {user.email}: {str(e)}")
    
    @user_status_updated.connect
    def on_user_status_updated(sender, user, old_status, new_status, **kwargs):
        """Handle user status update event."""
        logger.info(f"User status updated for {user.email}: {old_status} -> {new_status}")
        try:
            mail_service = MailService()
            is_approved = new_status == "active"
            is_suspended = new_status == "suspended"
            
            mail_service.send_user_status_updated_email(
                user.name,
                user.email,
                old_status,
                new_status,
                is_approved,
                is_suspended,
            )
        except Exception as e:
            logger.error(f"Failed to send status update email to {user.email}: {str(e)}")
