"""Routes package exports."""

from app.routes.auth import auth_bp
from .payment_routes import payment_bp
from app.routes.product import api_v1_bp  # 1. Import the master API blueprint

__all__ = ["auth_bp", "payment_bp", "api_v1_bp"]   # 2. Expose it to the application factory