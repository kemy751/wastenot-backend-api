from marshmallow import Schema, fields, validates, ValidationError
from app.models import UserStatus, UserRole


class SignupSchema(Schema):
    
    name = fields.String(required=True, validate=lambda x: len(x) >= 1)
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=lambda x: len(x) >= 6)
    role = fields.String(
        required=False,
        missing=UserRole.BUYER.value,
        validate=lambda x: x in [role.value for role in UserRole]
    )
    phone = fields.String(required=False)
    
    @validates("password")
    def validate_password(self, value):
        """Password must contain at least one digit."""
        if not any(char.isdigit() for char in value):
            raise ValidationError("Password must contain at least one digit.")


class LoginSchema(Schema):
    """Schema for user login."""
    
    email = fields.Email(required=True)
    password = fields.String(required=True)


class ChangePasswordSchema(Schema):
    """Schema for changing password."""
    
    old_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=lambda x: len(x) >= 6)
    
    @validates("new_password")
    def validate_new_password(self, value):
        if not any(char.isdigit() for char in value):
            raise ValidationError("Password must contain at least one digit.")


class ForgotPasswordSchema(Schema):
    
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    
    reset_token = fields.String(required=True)
    new_password = fields.String(required=True, validate=lambda x: len(x) >= 6)
    
    @validates("new_password")
    def validate_new_password(self, value):
        if not any(char.isdigit() for char in value):
            raise ValidationError("Password must contain at least one digit.")


class RefreshTokenSchema(Schema):
    
    refresh_token = fields.String(required=True)


class UpdateUserStatusSchema(Schema):
    
    email = fields.Email(required=True)
    status = fields.String(
        required=True,
        validate=lambda x: x in [status.value for status in UserStatus]
    )
