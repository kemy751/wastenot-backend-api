"""Services package exports."""

from app.services.auth_service import AuthService
from app.services.mail_service import MailService

# 1. Import your business logic services
# (Note: If your service classes are inside a file named something else like 'product.py' 
# or 'services.py', change '.product_service' to match your actual file name!)
from app.services.product_service import (
    ProductService,
    ListingService,
    ListingInterestService
)

# 2. Add them to the public package members list
__all__ = [
    "AuthService", 
    "MailService",
    "ProductService",
    "ListingService",
    "ListingInterestService"
]