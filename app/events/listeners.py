import logging
from app.events.signals import (
    user_registered,
    password_reset_requested,
    user_status_updated,
    seller_registered,
)
from app.services.mail_service import MailService

logger = logging.getLogger(__name__)

def register_event_listeners():
    
    @user_registered.connect
    def on_user_registered(sender, user, **kwargs):
        logger.info(f"User registered: {user.email}")
        try:
            mail_service = MailService()
            mail_service.send_welcome_email(user.name, user.email, user.role, user.status)
        except Exception as e:
            logger.error(f"Welcome email failed: {e}")
    
    @password_reset_requested.connect
    def on_password_reset_requested(sender, user, reset_link, **kwargs):
        logger.info(f"Password reset: {user.email}")
        try:
            mail_service = MailService()
            mail_service.send_password_reset_email(user.name, user.email, reset_link)
        except Exception as e:
            logger.error(f"Reset email failed: {e}")
    
    @seller_registered.connect
    def on_seller_registered(sender, user, seller_profile, **kwargs):
        logger.info(f"Seller registered: {user.email}")
        try:
            mail_service = MailService()
            mail_service.send_seller_confirmation_email(user.name, user.email)
            mail_service.send_seller_registration_admin_email(
                name=user.name,
                email=user.email,
                phone=user.phone or "",
                selfie_url=seller_profile.selfie_url,
                national_id_front_url=seller_profile.national_id_front_url,
                national_id_back_url=seller_profile.national_id_back_url,
            )
        except Exception as e:
            logger.error(f"Seller emails failed: {e}")
    
    @user_status_updated.connect
    def on_user_status_updated(sender, user, old_status, new_status, **kwargs):
        logger.info(f"Status update: {user.email} {old_status}->{new_status}")
        try:
            mail_service = MailService()
            is_approved = (new_status == "active")
            is_suspended = (new_status == "suspended")
            mail_service.send_user_status_updated_email(
                user.name, user.email, old_status, new_status, is_approved, is_suspended
            )
        except Exception as e:
            logger.error(f"Status email failed: {e}")