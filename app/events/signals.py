"""
Blinker signal definitions for the application event system.
"""

from app.extensions import events

# User events
user_registered = events.signal("user:registered")
password_reset_requested = events.signal("password:reset_requested")
user_status_updated = events.signal("user:status_updated")

# Delivery staff events
delivery_staff_registered = events.signal("delivery_staff:registered")

# Seller events (alias for delivery staff signal for compatibility)
seller_registered = delivery_staff_registered
