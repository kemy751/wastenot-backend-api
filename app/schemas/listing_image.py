from marshmallow import Schema, fields

class ListingImageSchema(Schema):
    id = fields.Str()
    image_url = fields.Str()
    sort_order = fields.Int()