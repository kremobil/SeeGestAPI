from db import db
from enums import ReportType

class PostReportModel(db.Model):
    __tablename__ = 'posts_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('UserModel')
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    post = db.relationship('PostModel')
    message = db.Column(db.String)
    type = db.Column(db.Enum(ReportType))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())