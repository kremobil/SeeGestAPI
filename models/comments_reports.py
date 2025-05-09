from db import db
from enums import ReportType


class CommentReportModel(db.Model):
    __tablename__ = 'comments_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('UserModel')
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    comment = db.relationship('CommentModel')
    message = db.Column(db.String)
    type = db.Column(db.Enum(ReportType))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())