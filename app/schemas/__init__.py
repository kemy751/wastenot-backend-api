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

# 1. Import your core business entity schemas
# (Note: If these schemas are located in a file with a different name, 
# change '.product_schemas' to match your actual file name, like '.schemas'!)
from app.schemas.product_schemas import (
    ProductSchema,
    ListingSchema,
    ListingInterestSchema
)

# Backwards-compatible alias
RegisterDeliveryStaffSchema = RegisterSellerSchema

# 2. Add them to the public namespace
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
    "ProductSchema",
    "ListingSchema",
    "ListingInterestSchema",
]