"""
Blinker signal definitions for the application event system.
"""

from app.extensions import events

# User events
user_registered = events.signal("user:registered")
password_reset_requested = events.signal("password:reset_requested")
user_status_updated = events.signal("user:status_updated")

seller_registered = events.signal("seller:registered")
