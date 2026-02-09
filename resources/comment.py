from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint, abort

from db import db
from models import CommentModel, PostModel, UserModel
from schemas import CommentSchema

blp = Blueprint('comment', __name__)

@blp.route('/comments')
class Comments(MethodView):

    @blp.response(200, CommentSchema(many=True))
    @jwt_required()
    def get(self):
        user = UserModel.query.get(get_jwt_identity())
        if user.is_admin is False and user.is_super_admin is False:
            abort(403, message="You don't have permission to view this endpoint")
        return CommentModel.query.filter_by(parent_comment_id=None).all()

    @jwt_required()
    @blp.arguments(CommentSchema(), location='json')
    @blp.response(201, CommentSchema())
    def post(self, comment_data: dict) -> db.Model:
        comment_data['user_id'] = get_jwt_identity()

        if PostModel.query.get(comment_data['post_id']) is None:
            abort(404, message='Post not found')

        if comment_data.get('content').strip() == '':
            abort(422, message='Content is required')

        if comment_data.get('parent_comment_id') is not None:
            parent_comment = CommentModel.query.get(comment_data['parent_comment_id'])
            if parent_comment is None:
                abort(404, message='Parent comment not found')
            if parent_comment.post_id != comment_data['post_id']:
                abort(422, message='Parent cant belong to another post')

        comment = CommentModel(**comment_data)

        comment.save()

        return comment

@blp.route('/post/<int:post_id>/comments')
class PostComments(MethodView):
    @blp.response(200, CommentSchema(many=True, exclude=["post", "replies", "parent_comment"]))
    def get(self, post_id):
        comments = CommentModel.query.filter_by(post_id=post_id, parent_comment_id=None).all()
        return comments

@blp.route('/comment/<int:comment_id>')
class Comment(MethodView):
    @blp.response(200, CommentSchema())
    def get(self, comment_id):
        comment = CommentModel.query.get(comment_id)
        if comment is None:
            abort(404, message='Comment not found')
        return comment
