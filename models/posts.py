from datetime import datetime

from db import db

class PostsModel(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    location = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    icon_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    icon = db.relationship('FileModel')
    tags = db.relationship('TagsModel', secondary='posts_tags', back_populates='posts', lazy='dynamic')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('UserModel', back_populates='posts')