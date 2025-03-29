from marshmallow import Schema, fields, validate


class UserSchema(Schema):
    login = fields.Str(required=True, validate=validate.Length(min=7, max=60))
    password = fields.Str(required=True, validate=validate.Length(min=7, max=60))
