from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import abort, Blueprint
from flask.views import MethodView
from sqlalchemy.exc import IntegrityError

from db import db
from models import CommentReportModel, UserModel, CommentModel, PostReportModel, PostModel
from schemas import CommentReportSchema, PostReportSchema

blp = Blueprint('report', __name__)

@blp.route('/comments-reports')
class Report(MethodView):

    @jwt_required()
    @blp.response(200, CommentReportSchema(many=True))
    def get(self):
        user = UserModel.query.get(get_jwt_identity())

        if user.is_admin is False and user.is_super_admin is False:
            abort(403, message="You don't have permission to view this endpoint")

        return CommentReportModel.query.all()

    @jwt_required()
    @blp.arguments(CommentReportSchema(), location="json")
    def post(self, report_data):
        report_data['user_id'] = get_jwt_identity()
        comment = CommentModel.query.get(report_data['comment_id'])

        if comment is None:
            abort(404, message="Comment not found")

        try:
            report = CommentReportModel(**report_data)
            db.session.add(report)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(500, message="Something went wrong")

        return {
            "message": "comment reported successfully",
        }


@blp.route('/posts-reports')
class PostReport(MethodView):
    @jwt_required()
    @blp.response(200, PostReportSchema(many=True))
    def get(self):
        user = UserModel.query.get(get_jwt_identity())
        if user.is_admin is False and user.is_super_admin is False:
            abort(403, message="You don't have permission to view this endpoint")

        return PostReportModel.query.all()

    @jwt_required()
    @blp.arguments(PostReportSchema(), location="json")
    def post(self, report_data):
        report_data['user_id'] = get_jwt_identity()

        post = PostModel.query.get(report_data['post_id'])

        if post is None:
            abort(404, message="Post not found")

        try:
            post = PostReportModel(**report_data)
            db.session.add(post)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

        return {
            "message": "post reported successfully",
        }


