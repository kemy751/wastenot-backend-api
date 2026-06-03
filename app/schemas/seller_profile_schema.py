from marshmallow import Schema, fields, validates, ValidationError


class SellerProfileSchema(Schema):
    id = fields.UUID(dump_only=True)
    user_id = fields.UUID(required=True)
    address = fields.String(allow_none=True)
    selfie_url = fields.Url()
    national_id_front_url = fields.Url()
    national_id_back_url = fields.Url()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
      
    @validates("password")
    def validate_password(self, value):
        if not any(char.isdigit() for char in value):
            raise ValidationError("Password must contain at least one digit.")
