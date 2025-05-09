from db import db
from sqlalchemy import func

class PasswordResetModel(db.Model):
    __tablename__ = 'password_resets'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('UserModel', backref='password_reset_code')
    created_at = db.Column(db.DateTime, default=func.current_timestamp())
    number_of_attempts = db.Column(db.Integer, default=0)