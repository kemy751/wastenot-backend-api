"""Schemas package exports."""

from app.schemas.auth_schemas import (
    SignupSchema,
    LoginSchema,
    ChangePasswordSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    RefreshTokenSchema,
    UpdateUserStatusSchema,
)
from app.schemas.seller_schemas import RegisterSellerSchema

# Backwards-compatible alias
RegisterDeliveryStaffSchema = RegisterSellerSchema

__all__ = [
    "SignupSchema",
    "LoginSchema",
    "ChangePasswordSchema",
    "ForgotPasswordSchema",
    "ResetPasswordSchema",
    "RefreshTokenSchema",
    "UpdateUserStatusSchema",
    "RegisterSellerSchema",
    "RegisterDeliveryStaffSchema",
]
