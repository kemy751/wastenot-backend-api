"""
Custom decorators for authorization and validation.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.models import User, UserRole
from app.extensions import db


def roles_required(*required_roles):
    """
    Decorator to enforce role-based access control.
    
    Must be used after @jwt_required() decorator.
    Queries the database to verify the user's role (not just trusting JWT).
    
    Usage:
        @app.route("/admin-only", methods=["GET"])
        @jwt_required()
        @roles_required("admin")
        def admin_endpoint():
            return {"message": "Admin access"}
    
    Args:
        *required_roles: Variable number of allowed role strings
    
    Returns:
        Decorated function that checks user roles
    """
    
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Get user ID from JWT
            user_id = get_jwt_identity()
            
            if not user_id:
                return jsonify({"error": "Unauthorized", "status_code": 401}), 401
            
            # Query database to get user and verify role
            user = db.session.get(User, user_id)
            
            if not user:
                return jsonify({"error": "User not found", "status_code": 404}), 404
            
            # Check if user's role is in required roles
            if user.role not in required_roles:
                return jsonify({
                    "error": "Insufficient permissions",
                    "status_code": 403
                }), 403
            
            return fn(*args, **kwargs)
        
        return wrapper
    
    return decorator
