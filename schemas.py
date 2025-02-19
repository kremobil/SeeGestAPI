from marshmallow import Schema, fields
from sqlalchemy.sql.functions import current_timestamp


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

class PlainTagSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(metadata={"description": "The tags's name"}, required=True)
    count = fields.Int(metadata={"description": "The number of posts this tag was used in"}, dump_only=True)


class TagSearchSchema(Schema):
    query = fields.Str(required=False)

class PlainPostSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(metadata={"description": "The post's title"}, required=True)
    content = fields.Str(metadata={"description": "The post's content"}, required=True)
    location = fields.Str(metadata={"description": "The post's location"}, required=True)
    created_at = fields.DateTime(metadata={"description": "The post's creation time."}, required=True)

class PostSchema(PlainPostSchema):
    icon = fields.Nested(PlainFileSchema(), dump_only=True)
    icon_id = fields.Int(required=True)
    tags = fields.Nested(PlainTagSchema(), many=True, dump_only=True)
    author = fields.Nested(lambda: UserSchema(exclude=['posts'], partial=True), dump_only=True)
    tags_ids = fields.List(fields.Int(required=True), required=True)


class TagSchema(PlainTagSchema):
    posts = fields.List(fields.Nested(PlainPostSchema), dump_only=True)

class UserSchema(PlainUserSchema):
    avatar_id = fields.Int(load_only=True)
    avatar = fields.Nested(PlainFileSchema(), dump_only=True)
    posts = fields.Nested(PostSchema(exclude=['author'], partial=True), many=True, dump_only=True)

class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class AvatarUploadSchema(Schema):
    image = fields.Raw(required=True, type="file")

class SocialLoginSchema(Schema):
    token = fields.Str(required=True)

class LocationAutocompleteSchema(Schema):
    query = fields.Str(required=True)
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
