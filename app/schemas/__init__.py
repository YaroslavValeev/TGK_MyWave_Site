from marshmallow import Schema, fields

class BookingSchema(Schema):
    date = fields.String(required=True)
    time = fields.String(required=True)
    name = fields.String(required=True)
    phone = fields.String(required=True)
    service_type = fields.String(required=False, load_default="gym", allow_none=True)
    set_count = fields.Integer(required=False, load_default=1, allow_none=True)