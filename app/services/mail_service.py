"""
Email service for sending transactional emails.
Uses Flask-Mail and Jinja2 templates.
"""

import logging
from os import name
from flask import Flask, render_template
from flask_mail import Mail, Message
from app.extensions import mail

logger = logging.getLogger(__name__)


class MailService:
    """Service for sending emails."""
    
    def __init__(self):
        """Initialize mail service."""
        self.mail = mail
    
    def send_welcome_email(self, name, email, role, status):
        """
        Send welcome email to new user.
        
        Args:
            name: User's name
            email: User's email address
            role: User's role
            status: User's status
        """
        try:
            html = render_template(
                "emails/welcome_user.html",
                name=name,
                email=email,
                role=role,
                status=status,
                is_pending_approval=(status == "pending_approval"),
            )
            
            msg = Message(
                subject="Welcome to Waste Not!",
                recipients=[email],
                html=html,
            )
            
            self.mail.send(msg)
            logger.info(f"Welcome email sent to {email}")
        except Exception as e:
            logger.error(f"Error sending welcome email to {email}: {str(e)}")
            raise
    
    def send_password_reset_email(self, user_name, email, reset_link):
        """
        Send password reset email.
        
        Args:
            user_name: User's name
            email: User's email address
            reset_link: Password reset link
        """
        try:
            html = render_template(
                "emails/password_reset.html",
                user_name=user_name,
                reset_link=reset_link,
            )
            
            msg = Message(
                subject="Reset Your Waste Not Password",
                recipients=[email],
                html=html,
            )
            
            self.mail.send(msg)
            logger.info(f"Password reset email sent to {email}")
        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {str(e)}")
            raise
    
    def send_seller_confirmation_email(self, name, email):

        try:
            html = render_template(
                "emails/seller_confirmation.html",
                name=name,
            )

            msg = Message(
                subject="Seller Application Received",
                recipients=[email],
                html=html,
            )

            self.mail.send(msg)
            logger.info(f"Seller confirmation email sent to {email}")
        except Exception as e:
            logger.error(f"Error sending seller confirmation email to {email}: {str(e)}")
            raise
    
    def send_seller_registration_admin_email(
        self, name, email, phone,
        vehicle_type, license_number, selfie_url,
        national_id_front_url, national_id_back_url
    ):
        """
        Send admin notification for new seller (formerly delivery staff).
        """
        try:
            admin_email = current_app.config.get("ADMIN_EMAIL", "admin@wastenot.com")

            html = render_template(
                "emails/seller_registration_admin.html",
                name=name,
                email=email,
                phone=phone,
                vehicle_type=vehicle_type,
                license_number=license_number,
                selfie_url=selfie_url,
                national_id_front_url=national_id_front_url,
                national_id_back_url=national_id_back_url,
            )

            msg = Message(
                subject="New Seller Registration",
                recipients=[admin_email],
                html=html,
            )

            self.mail.send(msg)
            logger.info(f"Seller admin notification sent for {email}")
        except Exception as e:
            logger.error(f"Error sending seller admin email for {email}: {str(e)}")
            raise
    
    def send_user_status_updated_email(
        self, name, email, old_status, new_status,
        is_approved, is_suspended
    ):
        """
        Send status update email to user.
        
        Args:
            user_name: User's name
            email: User's email
            old_status: Previous status
            new_status: New status
            is_approved: Whether user was approved
            is_suspended: Whether user was suspended
        """
        try:
            html = render_template(
                "emails/user_status_updated.html",
                name=name,
                old_status=old_status,
                new_status=new_status,
                is_approved=is_approved,
                is_suspended=is_suspended,
            )
            
            msg = Message(
                subject="Your Waste Not Account Status Updated",
                recipients=[email],
                html=html,
            )
            
            self.mail.send(msg)
            logger.info(f"Status update email sent to {email}")
        except Exception as e:
            logger.error(f"Error sending status update email to {email}: {str(e)}")
            raise


# Import current_app here to avoid circular imports
from flask import current_app
