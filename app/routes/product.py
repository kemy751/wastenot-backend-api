from flask import Blueprint, request, jsonify
from functools import wraps
from marshmallow import ValidationError
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from app.models import UserRole
from app.schemas import ProductSchema, ListingSchema, ListingInterestSchema
from app.services import ProductService, ListingService, ListingInterestService

# Initialize Blueprints
product_bp = Blueprint('products', __name__)
listing_bp = Blueprint('listings', __name__)
interest_bp = Blueprint('interests', __name__)

# Initialize Schemas
product_schema = ProductSchema()
listing_schema = ListingSchema()
interest_schema = ListingInterestSchema()


# --- RBAC SECURITY DECORATOR ---
def roles_required(*allowed_roles: UserRole):
    """
    Validates the caller's identity using JWT cryptographic signatures.
    Extracts identity strings and custom roles injected via login claims.
    """
    def decorator(f):
        @wraps(f)
        @jwt_required() # Rejects traffic missing valid Authorization Bearer headers
        def decorated_function(*args, **kwargs):
            claims = get_jwt()
            user_role_str = claims.get("role") # Extracts "admin", "seller", or "buyer"
            
            # Match the token's string role against valid enum value string targets
            if user_role_str not in [role.value for role in allowed_roles]:
                return jsonify({"message": "Access denied. Insufficient permissions."}), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =====================================================================
# PRODUCT ROUTES
# =====================================================================

@product_bp.route('/products', methods=['POST'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def create_product():
    try:
        json_data = request.get_json()
        data = product_schema.load(json_data)
        product = ProductService.create(data)
        return jsonify(product_schema.dump(product)), 201
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@product_bp.route('/products/<uuid:product_id>', methods=['GET'])
def get_product(product_id):
    product = ProductService.get_by_id(product_id)
    if not product:
        return jsonify({"message": "Product not found"}), 404
    return jsonify(product_schema.dump(product)), 200

@product_bp.route('/products', methods=['GET'])
def get_all_products():
    products = ProductService.get_all()
    return jsonify(product_schema.dump(products, many=True)), 200

@product_bp.route('/products/<uuid:product_id>', methods=['PATCH'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def patch_product(product_id):
    try:
        json_data = request.get_json()
        data = product_schema.load(json_data, partial=True) # partial allows isolated property tweaks
        updated_product = ProductService.update(product_id, data)
        if not updated_product:
            return jsonify({"message": "Product not found"}), 404
        return jsonify(product_schema.dump(updated_product)), 200
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@product_bp.route('/products/<uuid:product_id>', methods=['DELETE'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def delete_product(product_id):
    if ProductService.delete(product_id):
        return jsonify({"message": "Product successfully deleted"}), 200
    return jsonify({"message": "Product not found"}), 404


# =====================================================================
# LISTING ROUTES
# =====================================================================

@listing_bp.route('/listings', methods=['POST'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def create_listing():
    try:
        json_data = request.get_json()
        
        # Pulls the active signer's UUID straight out of the secure token
        json_data['seller_id'] = get_jwt_identity()
        
        data = listing_schema.load(json_data)
        listing = ListingService.create(data)
        return jsonify(listing_schema.dump(listing)), 201
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@listing_bp.route('/listings/<uuid:listing_id>', methods=['GET'])
def get_listing(listing_id):
    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing not found"}), 404
    return jsonify(listing_schema.dump(listing)), 200

@listing_bp.route('/listings', methods=['GET'])
def get_all_listings():
    listings = ListingService.get_all()
    return jsonify(listing_schema.dump(listings, many=True)), 200

@listing_bp.route('/listings/<uuid:listing_id>', methods=['PATCH'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def patch_listing(listing_id):
    try:
        listing = ListingService.get_by_id(listing_id)
        if not listing:
            return jsonify({"message": "Listing not found"}), 404
            
        # Security Guardrail: Prevent alternate sellers from editing this merchant's entry
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        if claims.get("role") != UserRole.ADMIN.value and str(listing.seller_id) != current_user_id:
            return jsonify({"message": "Unauthorized modification attempt"}), 403

        json_data = request.get_json()
        data = listing_schema.load(json_data, partial=True)
        updated_listing = ListingService.update(listing_id, data)
        return jsonify(listing_schema.dump(updated_listing)), 200
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@listing_bp.route('/listings/<uuid:listing_id>', methods=['DELETE'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def delete_listing(listing_id):
    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing not found"}), 404
        
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value and str(listing.seller_id) != current_user_id:
        return jsonify({"message": "Unauthorized modification attempt"}), 403

    ListingService.delete(listing_id)
    return jsonify({"message": "Listing successfully deleted"}), 200


# =====================================================================
# LISTING INTEREST ROUTES
# =====================================================================

@interest_bp.route('/listings/<uuid:listing_id>/interests', methods=['POST'])
@roles_required(UserRole.BUYER, UserRole.ADMIN) # ONLY buyers or admins can declare buy interests
def express_interest(listing_id):
    try:
        json_data = request.get_json() or {}
        json_data['listing_id'] = str(listing_id)
        json_data['buyer_id'] = get_jwt_identity() # Bound straight to verified buyer token identity
        
        data = interest_schema.load(json_data)
        interest = ListingInterestService.create(data)
        return jsonify(interest_schema.dump(interest)), 201
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@interest_bp.route('/listings/<uuid:listing_id>/interests', methods=['GET'])
@roles_required(UserRole.SELLER, UserRole.ADMIN) # Only store owners read interest backlogs
def get_listing_waitlist(listing_id):
    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing reference invalid"}), 404
        
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value and str(listing.seller_id) != current_user_id:
        return jsonify({"message": "Access unauthorized"}), 403

    interests = ListingInterestService.get_all_for_listing(listing_id)
    return jsonify(interest_schema.dump(interests, many=True)), 200

@interest_bp.route('/interests/<uuid:interest_id>', methods=['PATCH'])
@roles_required(UserRole.SELLER, UserRole.ADMIN) # Sellers accept/reject waitlist options
def patch_interest_status(interest_id):
    try:
        json_data = request.get_json()
        data = interest_schema.load(json_data, partial=True)
        
        updated_interest = ListingInterestService.update(interest_id, data)
        if not updated_interest:
            return jsonify({"message": "Interest record not found"}), 404
        return jsonify(interest_schema.dump(updated_interest)), 200
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400