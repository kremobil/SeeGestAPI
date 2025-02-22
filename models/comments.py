from time import sleep

from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property

from db import db

class CommentModel(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.relationship('UserModel', back_populates='comments')
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    post = db.relationship('PostModel', back_populates='comments', lazy=True)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    path = db.Column(db.String, nullable=True)

    parent_comment = db.relationship('CommentModel', remote_side=[id], back_populates='replies')
    replies = db.relationship('CommentModel', back_populates='parent_comment', lazy='dynamic')

    @db.ext.hybrid.hybrid_property
    def depth(self):
        return len(self.path.split('.')) if self.path else 0

    def save(self):
        try:
            db.session.add(self)
            db.session.flush()

            if self.parent_comment_id is None:
                self.path = str(self.id)
            else:
                self.path = f"{self.parent_comment.path}.{self.id}"

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e