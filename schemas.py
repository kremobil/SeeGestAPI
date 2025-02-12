from marshmallow import Schema, fields

class PlainUserSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(metadata={"description": "The user's name"}, required=True)
    surname = fields.Str(metadata={"description": "The user's surname"}, required=True)
    birthdate = fields.Date(metadata={"description": "The user's birthdate"}, required=True)
    city = fields.Str(metadata={"description": "The user's city"}, required=True)
    email = fields.Email(metadata={"description": "The user's email"}, load_only=True, required=True)
    password = fields.Str(metadata={"description": "The user's password"}, load_only=True, required=True)
    created = fields.DateTime(
        dump_only=True,
        dump_default=lambda dt: dt.isoformat(),
        metadata={"default": "The current datetime"},
    )

class PlainFileSchema(Schema):
    id = fields.Int(dump_only=True)
    filename = fields.Str(required=True)
    url = fields.Str(required=True)
    upload_date = fields.DateTime(dump_only=True)
    mime_type = fields.Str(required=True)
    size = fields.Int(required=True)

class UserSchema(PlainUserSchema):
    avatar_id = fields.Int(load_only=True)
    avatar = fields.Nested(PlainFileSchema(), dump_only=True)

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class AvatarUploadSchema(Schema):
    image = fields.Raw(required=True, type="file")

class SocialLoginSchema(Schema):
    token = fields.Str(required=True)