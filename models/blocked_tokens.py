from email.policy import default

from db import db

class BlockedTokenModel(db.Model):
    __tablename__ = 'blocked_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String, nullable=False)
    blocked_at = db.Column(db.DateTime, default=db.func.current_timestamp())
