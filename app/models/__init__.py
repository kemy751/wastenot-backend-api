"""Models package exports."""

from app.models.user import User, UserRole, UserStatus
from app.models.refresh_token import RefreshToken
from app.models.reset_token import ResetToken
from app.models.seller_profile import SellerProfile
from app.models.product import (
    ElectronicType, ItemCondition, ListingStatus, InterestStatus,
    Product, Listing, ListingInterest
)

# 1. Import your enums AND the database model classes
# (Change '.product_models' to your actual file name if it's different!)
from app.models.product import (
    ElectronicType, 
    ItemCondition, 
    ListingStatus, 
    InterestStatus,
    Product,          # <-- Added database model
    Listing,          # <-- Added database model
    ListingInterest   # <-- Added database model
)

# Backwards-compatible alias (some modules may still import DeliveryStaff)
Seller = SellerProfile
DeliveryStaff = SellerProfile

# 2. Add the database model classes to your exposed members list
__all__ = [
    "User",
    "UserRole",
    "UserStatus",
    "RefreshToken",
    "ResetToken",
    "Seller",
    "DeliveryStaff",
    "ElectronicType",
    "ItemCondition",
    "ListingStatus",
    "InterestStatus",
    "Product",          # <-- Exposed here
    "Listing",          # <-- Exposed here
    "ListingInterest",  # <-- Exposed here
]