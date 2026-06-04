from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from app.models import User
from app.extensions import db

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.method == "OPTIONS":
                return "", 200

            @jwt_required()
            def protected():
                claims = get_jwt()
                user_role = claims.get("role")

                # Convert allowed_roles to a list of strings (handle both Enum and str)
                allowed_role_values = []
                for role in allowed_roles:
                    if hasattr(role, 'value'):
                        allowed_role_values.append(role.value)
                    else:
                        allowed_role_values.append(str(role))

                if user_role not in allowed_role_values:
                    return jsonify({"message": "Access denied"}), 403

                return f(*args, **kwargs)

            return protected()

        return wrapper
    return decorator