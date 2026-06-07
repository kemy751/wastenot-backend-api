from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from marshmallow import ValidationError
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import uuid
import os
from app.extensions import db
from sqlalchemy import func
from werkzeug.utils import secure_filename

from app.models import UserRole, ListingInterest, InterestStatus
from app.models.listing_image import ListingImage
from app.models.product import Listing
from app.schemas import ProductSchema, ListingSchema, ListingInterestSchema
from app.services import ProductService, ListingService, ListingInterestService

# Initialize Base Sub-Blueprints
product_bp = Blueprint('products', __name__)
listing_bp = Blueprint('listings', __name__)
interest_bp = Blueprint('interests', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def roles_required(*allowed_roles: UserRole):
    """RBAC decorator"""
    def decorator(f):
        @wraps(f)
        @jwt_required()
        def decorated_function(*args, **kwargs):
            claims = get_jwt()
            user_role_str = claims.get("role")
            if user_role_str not in [role.value for role in allowed_roles]:
                return jsonify({"message": "Access denied. Insufficient permissions."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =====================================================================
# PRODUCT ROUTES
# =====================================================================

@product_bp.route('/products', methods=['POST', 'OPTIONS'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def create_product():
    try:
        json_data = request.get_json() or {}
        current_user_id = get_jwt_identity()
        json_data['seller_id'] = current_user_id
        data = ProductSchema().load(json_data)
        product = ProductService.create(data)
        return jsonify(ProductSchema().dump(product)), 201
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@product_bp.route('/products/<uuid:product_id>', methods=['GET'])
def get_product(product_id):
    product = ProductService.get_by_id(product_id)
    if not product:
        return jsonify({"message": "Product not found"}), 404
    return jsonify(ProductSchema().dump(product)), 200

@product_bp.route('/products', methods=['GET'])
def get_all_products():
    products = ProductService.get_all()
    return jsonify(ProductSchema().dump(products, many=True)), 200

@product_bp.route('/products/<uuid:product_id>', methods=['PATCH'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def patch_product(product_id):
    product = ProductService.get_by_id(product_id)
    if not product:
        return jsonify({"message": "Product not found"}), 404
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value and str(product.seller_id) != current_user_id:
        return jsonify({"message": "Unauthorized modification attempt"}), 403
    try:
        json_data = request.get_json() or {}
        data = ProductSchema().load(json_data, partial=True)
        updated_product = ProductService.update(product_id, data)
        return jsonify(ProductSchema().dump(updated_product)), 200
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@product_bp.route('/products/<uuid:product_id>', methods=['DELETE'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def delete_product(product_id):
    product = ProductService.get_by_id(product_id)
    if not product:
        return jsonify({"message": "Product not found"}), 404
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value and str(product.seller_id) != current_user_id:
        return jsonify({"message": "Unauthorized modification attempt"}), 403
    ProductService.delete(product_id)
    return jsonify({"message": "Product successfully deleted"}), 200


# =====================================================================
# LISTING ROUTES
# =====================================================================

@listing_bp.route('/listings', methods=['POST'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def create_listing():
    try:
        json_data = request.get_json() or {}
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        if claims.get("role") != UserRole.ADMIN.value:
            json_data['seller_id'] = current_user_id
        else:
            if 'seller_id' not in json_data:
                return jsonify({"message": "Validation failed", "errors": {"seller_id": ["Admins must provide seller_id"]}}), 400
        raw_product_id = json_data.get('product_id')
        if not raw_product_id:
            return jsonify({"message": "Missing product_id parameter"}), 400
        try:
            product_uuid = uuid.UUID(str(raw_product_id))
        except ValueError:
            return jsonify({"message": "Invalid product_id format"}), 400
        product = ProductService.get_by_id(product_uuid)
        if not product:
            return jsonify({"message": "Product not found"}), 404
        if claims.get("role") != UserRole.ADMIN.value and str(product.seller_id) != current_user_id:
            return jsonify({"message": "Unauthorized: You do not own this product record"}), 403
        data = ListingSchema().load(json_data)
        listing = ListingService.create(data)
        return jsonify(ListingSchema().dump(listing)), 201
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400

@listing_bp.route('/listings/<uuid:listing_id>', methods=['GET'])
def get_listing(listing_id):
    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing not found"}), 404
    # Increment view count
    try:
        if hasattr(listing, 'views') and listing.views is not None:
            listing.views = (listing.views or 0) + 1
        else:
            listing.views = 1
        db.session.commit()
    except Exception:
        db.session.rollback()  # Don't fail the request if view tracking fails
    return jsonify(ListingSchema().dump(listing)), 200

@listing_bp.route('/listings', methods=['GET'])
def get_all_listings():
    listings = ListingService.get_all()
    return jsonify(ListingSchema().dump(listings, many=True)), 200

@listing_bp.route('/listings/<uuid:listing_id>', methods=['PATCH'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def patch_listing(listing_id):
    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing not found"}), 404
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value and str(listing.seller_id) != current_user_id:
        return jsonify({"message": "Unauthorized modification attempt"}), 403
    try:
        json_data = request.get_json() or {}
        data = ListingSchema().load(json_data, partial=True)
        updated_listing = ListingService.update(listing_id, data)
        return jsonify(ListingSchema().dump(updated_listing)), 200
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

# ========== IMAGE ROUTES ==========
@listing_bp.route('/listings/<listing_id>/images', methods=['GET'])
def get_listing_images(listing_id):
    listing = Listing.query.get(listing_id)
    if not listing:
        return jsonify({"message": "Listing not found"}), 404
    # Query images directly from the ListingImage table
    images = ListingImage.query.filter_by(listing_id=listing.id).order_by(ListingImage.sort_order).all()
    return jsonify([{"id": img.id, "url": img.image_url, "order": img.sort_order} for img in images]), 200


@listing_bp.route('/listings/<listing_id>/images', methods=['POST'])
@jwt_required()
def upload_listing_images(listing_id):
    user_id = get_jwt_identity()
    listing = Listing.query.get(listing_id)
    if not listing or listing.seller_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    if 'images' not in request.files:
        return jsonify({"message": "No images provided"}), 400
    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({"message": "No selected files"}), 400
    max_order = db.session.query(func.max(ListingImage.sort_order)).filter_by(listing_id=listing.id).scalar() or -1
    uploaded = []
    for idx, file in enumerate(files):
        if not allowed_file(file.filename):
            continue
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        from app.utils.cloudinary_helper import upload_file
        image_url = upload_file(file, folder="greentag/listings")
        listing_image = ListingImage(
            listing_id=listing.id,
            image_url=image_url,
            sort_order=max_order + idx + 1
        )
        db.session.add(listing_image)
        uploaded.append(image_url)
    db.session.commit()
    return jsonify({"message": "Images uploaded", "urls": uploaded}), 201

@listing_bp.route('/images/<image_id>', methods=['DELETE'])
@jwt_required()
def delete_listing_image(image_id):
    user_id = get_jwt_identity()
    image = ListingImage.query.get(image_id)
    if not image:
        return jsonify({"message": "Image not found"}), 404
    listing = image.listing
    if listing.seller_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], os.path.basename(image.image_url))
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(image)
    db.session.commit()
    return jsonify({"message": "Image deleted"}), 200

@listing_bp.route('/listings/<listing_id>/images/reorder', methods=['PATCH'])
@jwt_required()
def reorder_listing_images(listing_id):
    user_id = get_jwt_identity()
    listing = Listing.query.get(listing_id)
    if not listing or listing.seller_id != user_id:
        return jsonify({"message": "Unauthorized"}), 403
    data = request.get_json()
    image_ids = data.get('image_ids', [])
    for order, img_id in enumerate(image_ids):
        db.session.query(ListingImage).filter_by(id=img_id, listing_id=listing.id).update({'sort_order': order})
    db.session.commit()
    return jsonify({"message": "Order updated"}), 200

# =====================================================================
# LISTING INTEREST ROUTES
# =====================================================================

@interest_bp.route('/listings/<uuid:listing_id>/interests', methods=['POST'])
@roles_required(UserRole.BUYER, UserRole.ADMIN)
def express_interest(listing_id):
    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing reference invalid"}), 404

    try:
        json_data = request.get_json() or {}
        json_data['listing_id'] = str(listing_id)
        json_data['buyer_id'] = get_jwt_identity() 
        
        data = ListingInterestSchema().load(json_data)
        interest = ListingInterestService.create(data)
        return jsonify(ListingInterestSchema().dump(interest)), 201
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400


@interest_bp.route('/listings/<uuid:listing_id>/collect', methods=['POST'])
@roles_required(UserRole.BUYER, UserRole.ADMIN)
def buyer_collect_listing(listing_id):
    """
    Buyer confirms physical collection of a device.
    1. Verifies the buyer has an APPROVED interest on this listing.
    2. Updates the listing status to PENDING_SALE.
    3. Updates the interest status to COMPLETED.
    Called from BuyerClaimed → Mark as Collected button.
    """
    current_user_id = str(get_jwt_identity()).lower()

    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing not found"}), 404

    # Find the buyer's approved interest for this listing
    interest = ListingInterest.query.filter_by(
        listing_id=str(listing_id),
        buyer_id=current_user_id,
        status=InterestStatus.APPROVED,
    ).first()

    if not interest:
        return jsonify({"message": "No approved interest found for this listing"}), 403

    try:
        # Update listing → PENDING_SALE
        ListingService.update(listing_id, {"status": "PENDING_SALE"})

        # Update interest → COMPLETED
        ListingInterestService.update_specific_interest(
            interest.id, {"status": "COMPLETED"}
        )

        return jsonify({"message": "Device marked as collected successfully"}), 200
    except Exception as e:
        return jsonify({"message": f"Collection failed: {str(e)}"}), 500


@interest_bp.route('/listings/<uuid:listing_id>/interests', methods=['GET'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def get_listing_waitlist(listing_id):
    listing = ListingService.get_by_id(listing_id)
    if not listing:
        return jsonify({"message": "Listing reference invalid"}), 404
        
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    if claims.get("role") != UserRole.ADMIN.value and str(listing.seller_id) != current_user_id:
        return jsonify({"message": "Access unauthorized"}), 403

    interests = ListingInterestService.get_all_for_listing(listing_id)
    return jsonify(ListingInterestSchema().dump(interests, many=True)), 200


@interest_bp.route('/interests/<uuid:interest_id>/update', methods=['PATCH'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def patch_interest_status(interest_id):
    interest = ListingInterestService.get_by_id(interest_id)
    if not interest:
        return jsonify({"message": "Interest record not found"}), 404
        
    listing = ListingService.get_by_id(interest.listing_id)
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    if claims.get("role") != UserRole.ADMIN.value and str(listing.seller_id) != current_user_id:
        return jsonify({"message": "Unauthorized modification attempt"}), 403

    try:
        json_data = request.get_json() or {}
        allowed_updates = {"status": json_data.get("status")} 
        data = ListingInterestSchema().load(allowed_updates, partial=True)
        
        updated_interest = ListingInterestService.update_specific_interest(interest_id, data)
        return jsonify(ListingInterestSchema().dump(updated_interest)), 200
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400
# =====================================================================
# DASHBOARD / CONSOLIDATED VIEW ROUTES
# =====================================================================

# 1. Seller: Get their own listings (Optional filter: ?status=AVAILABLE)
@listing_bp.route('/me/listings', methods=['GET'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def get_my_listings():
    status = request.args.get('status')
    current_user_id = get_jwt_identity()
    listings = ListingService.get_listings_by_seller(current_user_id, status)
    
    result = []
    for listing in listings:
        # Serialize using your existing schema
        listing_dict = ListingSchema().dump(listing)
        # Add images manually
        listing_dict['images'] = [
            {"id": img.id, "image_url": img.image_url, "sort_order": img.sort_order}
            for img in listing.images
        ]
        result.append(listing_dict)
    
    return jsonify(result), 200

# 2. Seller: Get all interests received on their listings
@interest_bp.route('/me/received-interests', methods=['GET'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def get_received_interests():
    current_user_id = get_jwt_identity()
    interests = ListingInterestService.get_interests_by_seller_listings(current_user_id)
    return jsonify(ListingInterestSchema(many=True).dump(interests)), 200

# 3. Buyer: Get all my expressed interests (My Buys)
@interest_bp.route('/me/my-interests', methods=['GET'])
@roles_required(UserRole.BUYER, UserRole.ADMIN)
def get_my_sent_interests():
    current_user_id = get_jwt_identity()
    interests = ListingInterestService.get_interests_by_buyer(current_user_id)
    return jsonify(ListingInterestSchema(many=True).dump(interests)), 200

# app/routes.py

# =====================================================================
# FILTERED GET ROUTES
# =====================================================================

@listing_bp.route('/listings/status/<string:status_name>', methods=['GET'])
def get_listings_by_status(status_name):
    """
    Example: GET /api/v1/listings/status/AVAILABLE
    """
    listings = ListingService.get_by_status(status_name)
    return jsonify(ListingSchema(many=True).dump(listings)), 200


@interest_bp.route('/interests/status/<string:status_name>', methods=['GET'])
@roles_required(UserRole.SELLER, UserRole.ADMIN)
def get_interests_by_status(status_name):
    """
    Example: GET /api/v1/interests/status/EXPRESSED
    """
    interests = ListingInterestService.get_by_status(status_name)
    return jsonify(ListingInterestSchema(many=True).dump(interests)), 200


# =====================================================================
# INDIVIDUAL INTEREST UPDATE ROUTE
# =====================================================================

@interest_bp.route('/interests/<uuid:interest_id>/update', methods=['PATCH'])
@roles_required(UserRole.BUYER, UserRole.SELLER, UserRole.ADMIN)
def patch_specific_interest(interest_id):
    """
    Example: PATCH /api/v1/interests/847d2f29-1428-465c-8066-a7526fc84293/update
    """
    interest = ListingInterestService.get_by_id(interest_id)
    if not interest:
        return jsonify({"message": "Interest record not found"}), 404

    # Force cast IDs and strings to lower/upper spaces to stop comparison bugs
    current_user_id = str(get_jwt_identity()).lower()
    claims = get_jwt()
    user_role = str(claims.get("role", "")).upper()

    # --- GRANULAR RBAC SECURITY CHECK ---
    # Admins can bypass anything.
    if user_role != str(UserRole.ADMIN.value).upper():
        
        # Buyers can only update their own sent message expressions
        if user_role == str(UserRole.BUYER.value).upper():
            if str(interest.buyer_id).lower() != current_user_id:
                return jsonify({"message": "Unauthorized: This is not your interest record"}), 403
                
        # Sellers can only update incoming status updates on items they actually own
        elif user_role == str(UserRole.SELLER.value).upper():
            listing = ListingService.get_by_id(interest.listing_id)
            if not listing or str(listing.seller_id).lower() != current_user_id:
                return jsonify({"message": "Unauthorized: You do not own the parent listing asset"}), 403
    # ------------------------------------

    try:
        json_data = request.get_json() or {}
        
        # Partially load via Marshmallow to strip out read-only injected fields
        data = ListingInterestSchema().load(json_data, partial=True)
        
        updated_interest = ListingInterestService.update_specific_interest(interest_id, data)
        return jsonify(ListingInterestSchema().dump(updated_interest)), 200
        
    except ValidationError as err:
        return jsonify({"message": "Validation failed", "errors": err.messages}), 400
    # =====================================================================
# ADMINISTRATIVE DISCOVERY ROUTES
# =====================================================================

@listing_bp.route('/sellers/<uuid:seller_id>/listings', methods=['GET'])
@roles_required(UserRole.ADMIN)
def get_listings_by_explicit_seller(seller_id):
    """
    Administrative lookup endpoint to view any targeted seller's inventory.
    Optional Filter: ?status=AVAILABLE
    Example: GET /api/v1/sellers/31b9d4e1-2251-4f74-8909-a019afbfa4e0/listings
    """
    status_filter = request.args.get('status')
    
    # Safely cast the URL UUID parameter to match your db.String(36) column type
    clean_seller_str = str(seller_id).lower()
    
    # Query database records directly via your existing service engine layout
    listings = ListingService.get_listings_by_seller(clean_seller_str, status_filter)
    
    return jsonify(ListingSchema(many=True).dump(listings)), 200

# =====================================================================
# API COUPLING ENGINE & CENTRAL V1 REGISTRATION
# =====================================================================

# 1. Create the central master router blueprint for version 1
api_v1_bp = Blueprint('api_v1', __name__)

# 2. Attach your structural sub-blueprints directly to the version 1 parent node
api_v1_bp.register_blueprint(product_bp)
api_v1_bp.register_blueprint(listing_bp)
api_v1_bp.register_blueprint(interest_bp)