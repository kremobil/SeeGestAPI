import typing

from marshmallow import Schema, fields

from enums import ReportType
from models import PostModel, CommentModel


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
    latitude = fields.Float(metadata={"description": "The post's latitude"}, required=True)
    longitude = fields.Float(metadata={"description": "The post's longitude"}, required=True)
    created_at = fields.DateTime(metadata={"description": "The post's creation time."}, required=True)

class PlainIconSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(metadata={"description": "The icons's name"}, required=True)

class PlainCommentSchema(Schema):
    id = fields.Int(dump_only=True)
    content = fields.Str(metadata={"description": "The comment's content"}, required=True)
    created_at = fields.DateTime(metadata={"description": "The comment's creation time."}, dump_only=True)
    depth = fields.Int(metadata={"description": "The comment's depth"}, dump_only=True)

class IconSchema(PlainIconSchema):
    file_id = fields.Int(required=True, load_only=True)
    file = fields.Nested(PlainFileSchema(), dump_only=True)


class PostSchema(PlainPostSchema):
    icon = fields.Nested(IconSchema(), dump_only=True)
    icon_id = fields.Int(required=True)
    tags = fields.Nested(PlainTagSchema(), many=True, dump_only=True)
    author = fields.Nested(lambda: UserSchema(only=['avatar', 'name'], partial=True), dump_only=True)
    tags_ids = fields.List(fields.Int(required=True), required=True)
    comments = fields.Nested(PlainCommentSchema(), many=True, dump_only=True)

class PlainReportSchema(Schema):
    id = fields.Int(dump_only=True)
    message = fields.Str(metadata={"description": "The report's message"}, required=True)
    type = fields.Enum(ReportType, required=True)
    created_at = fields.DateTime(metadata={"description": "The report's creation time."}, dump_only=True)


class TagSchema(PlainTagSchema):
    posts = fields.List(fields.Nested(PlainPostSchema), dump_only=True)

class UserSchema(PlainUserSchema):
    avatar_id = fields.Int(load_only=True)
    avatar = fields.Nested(PlainFileSchema(), dump_only=True)
    posts = fields.Nested(PostSchema(exclude=['author', 'comments'], partial=True), many=True, dump_only=True)
    comments = fields.List(fields.Nested(PlainCommentSchema), dump_only=True)

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

class LocationSearchSchema(Schema):
    place_id = fields.Str(required=True)

class CommentSchema(PlainCommentSchema):
    post_id = fields.Int(required=True, load_only=True)
    post = fields.Nested(PlainPostSchema(), dump_only=True)
    author = fields.Nested(UserSchema(only=['avatar', 'name'], partial=True), dump_only=True)
    parent_comment_id = fields.Int(required=False, load_only=True)
    parent_comment = fields.Nested(PlainCommentSchema(), dump_only=True)
    replies = fields.List(fields.Nested('self', exclude=['post'], partial=True), dump_only=True)
    path = fields.Str(dump_only=True)

class ChangePasswordSchema(Schema):
    old_password = fields.Str(required=True)
    new_password = fields.Str(required=True)
    new_password_confirmation = fields.Str(required=True)

class CommentReportSchema(PlainReportSchema):
    comment_id = fields.Int(required=True, load_only=True)
    comment = fields.Nested(CommentSchema(exclude=['replies'], partial=True), dump_only=True)
    user = fields.Nested(UserSchema(exclude=['comments', 'posts'], partial=True), dump_only=True)

class PostReportSchema(PlainReportSchema):
    post_id = fields.Int(required=True, load_only=True)
    post = fields.Nested(PostSchema(exclude=['comments'], partial=True), dump_only=True)
    user = fields.Nested(UserSchema(exclude=['comments', 'posts'], partial=True), dump_only=True)

class SearchPostSchema(Schema):
    position = fields.Nested({
        "longitude": fields.Float(required=True),
        "latitude": fields.Float(required=True),
    })
    date_from = fields.DateTime()
    date_to = fields.DateTime()
    tags_ids = fields.List(fields.Int(required=True), required=False)

class GenericRelationField(fields.Field):

    def _serialize(
        self, value: typing.Any, attr: str | None, obj: typing.Any, **kwargs
    ) -> typing.Any:
        print(value)
        if value is None:
            return None

        if isinstance(value, PostModel):
            return PostSchema().dump(value)
        elif isinstance(value, CommentModel):
            return CommentSchema().dump(value)

        raise ValueError("Unsupported type")

class PlainNotificationSchema(Schema):
    id = fields.Int(dump_only=True)
    message = fields.Str(required=True)
    created_at = fields.DateTime(metadata={"description": "The notification's creation time."}, dump_only=True)
    is_read = fields.Bool(dump_only=True)

class NotificationSchema(PlainNotificationSchema):
    responder = fields.Nested(UserSchema(only=['avatar', 'name'], partial=True), dump_only=True)
    subject_type = fields.Str(required=True)
    subject_id = fields.Int(required=True)
    subject = GenericRelationField(required=True)



