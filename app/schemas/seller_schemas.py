from marshmallow import Schema, fields, validates, ValidationError


class RegisterSellerSchema(Schema):
    
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=lambda x: len(x) >= 6)
    first_name = fields.String(required=True, validate=lambda x: len(x) >= 1)
    last_name = fields.String(required=True, validate=lambda x: len(x) >= 1)
    phone = fields.String(required=True)
    vehicle_type = fields.String(required=True)
    license_number = fields.String(required=True)
    address = fields.String(required=False)
    selfie_url = fields.URL(required=True)
    national_id_front_url = fields.URL(required=True)
    national_id_back_url = fields.URL(required=True)
    
    @validates("password")
    def validate_password(self, value):
        if not any(char.isdigit() for char in value):
            raise ValidationError("Password must contain at least one digit.")
