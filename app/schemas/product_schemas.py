from marshmallow import Schema, fields, validate
from app.models import ElectronicType, ItemCondition, ListingStatus, InterestStatus

class ProductSchema(Schema):
    id = fields.UUID(dump_only=True)
    brand = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    model_name = fields.Str(required=True, validate=validate.Length(min=1, max=150))

    seller_id = fields.UUID(required=True)
    
    # Leverages Marshmallow's Enum processor to auto-map strings to Enum objects
    electronic_type = fields.Enum(ElectronicType, by_value=True, required=True)
    
    # Added sustainability metadata fields matching your database tracking strategy
    weight_kg = fields.Float(allow_none=True, validate=validate.Range(min=0.0))
    release_year = fields.Int(allow_none=True, validate=validate.Range(min=1970, max=2100))
    has_lithium_battery = fields.Bool(load_default=False)
    
    # Read-only cache score returned to users
    estimated_carbon_saved_kg = fields.Float(dump_only=True)


class ListingSchema(Schema):
    id = fields.UUID(dump_only=True)
    seller_id = fields.UUID(required=True)
    product_id = fields.UUID(required=True)
    price = fields.Decimal(required=True, places=2, as_string=True, validate=validate.Range(min=0.0))
    condition = fields.Enum(ItemCondition, by_value=True, required=True)
    is_working = fields.Bool(required=True)
    condition_notes = fields.Str(allow_none=True)
    status = fields.Enum(ListingStatus, by_value=True, load_default=ListingStatus.AVAILABLE)
    
    # NESTED: This allows listing results to show the full product info
    product = fields.Nested(ProductSchema, dump_only=True)
    interest_count = fields.Method("get_interest_count", dump_only=True)
    def get_interest_count(self, obj):
        # Assumes your Listing model has a relationship named 'interests'
        # e.g., interests = db.relationship('ListingInterest', backref='listing')
        return len(obj.interests) if hasattr(obj, 'interests') else 0
    created_at = fields.DateTime(dump_only=True)


class ListingInterestSchema(Schema):
    id = fields.UUID(dump_only=True)
    listing_id = fields.UUID(required=True)
    buyer_id = fields.UUID(required=True)
    message = fields.Str(allow_none=True)
    status = fields.Enum(InterestStatus, by_value=True, load_default=InterestStatus.EXPRESSED)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # NESTED: This allows interest results to show full listing and carbon/product info
    listing = fields.Nested(ListingSchema, dump_only=True, exclude=["interest_count"])
    
    # Existing fields
    listing_title = fields.Str(dump_only=True)
    seller_phone = fields.Str(dump_only=True)
    seller_name = fields.Str(dump_only=True)