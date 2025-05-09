from db import db

class TagsModel(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)
    posts = db.relationship('PostModel', secondary="posts_tags", back_populates='tags', lazy='dynamic')
    count = db.Column(db.Integer, nullable=False, default=0)

