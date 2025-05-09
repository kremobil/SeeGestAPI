from db import db

class PostsTagsModel(db.Model):
    __tablename__ = 'posts_tags'

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))