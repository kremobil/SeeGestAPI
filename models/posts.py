from datetime import datetime

from db import db

class Posts(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    location = db.Column(db.String, nullable=False)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    tags = db.relationship('Tags', secondary='posts_tags', backref='posts', lazy='dynamic')