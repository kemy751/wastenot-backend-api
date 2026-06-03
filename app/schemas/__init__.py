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
from app.schemas.product_schemas import ProductSchema, ListingSchema, ListingInterestSchema

# Simple profile update schema
from marshmallow import Schema, fields

class UpdateProfileSchema(Schema):
    name = fields.String(required=False)
    phone = fields.String(required=False)

__all__ = [
    "SignupSchema",
    "LoginSchema",
    "ChangePasswordSchema",
    "ForgotPasswordSchema",
    "ResetPasswordSchema",
    "RefreshTokenSchema",
    "UpdateUserStatusSchema",
    "ProductSchema",
    "ListingSchema",
    "ListingInterestSchema",
    "UpdateProfileSchema",
]