from db import db

class UserModel(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    birthdate = db.Column(db.DateTime())
    city = db.Column(db.String(80))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(72))
    created = db.Column(db.DateTime(), nullable=False, default=db.func.current_timestamp())
    avatar_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False, default=1)
    avatar = db.relationship('FileModel', foreign_keys=[avatar_id])
    posts = db.relationship('PostModel', back_populates='author', lazy='dynamic')
    comments = db.relationship('CommentModel', back_populates='author', lazy='dynamic')
    google_user_id = db.Column(db.Integer, index=True)
    facebook_user_id = db.Column(db.Integer, index=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_super_admin = db.Column(db.Boolean, nullable=False, default=False)