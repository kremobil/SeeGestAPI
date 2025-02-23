from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import generic_relationship
from sqlalchemy import func

from db import db


class NotificationModel(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('UserModel', back_populates='notifications', foreign_keys=[user_id])
    responder_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    responder = db.relationship('UserModel', foreign_keys=[responder_id])
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=func.current_timestamp())

    # relation to dynamic subject Either post or comment
    subject_type = db.Column(db.String(50))
    subject_id = db.Column(db.Integer)
    subject = generic_relationship(subject_type, subject_id)

    @hybrid_property
    def message(self):
        return f"Użytkownik {self.responder.name} {'skomentował twój Post' if self.subject_type == 'PostModel' else 'odpowiedział na twój Komentarz'}!"

    @classmethod
    def create_notification(cls, subject: db.Model, responder_id: db.Integer):
        subject_type = subject.__class__.__name__

        if subject_type == 'PostModel':
            notification = cls(user_id=subject.author_id, responder_id=responder_id, subject=subject)
            db.session.add(notification)
            db.session.commit()

            return notification
        elif subject_type == 'CommentModel':
            notification = cls(user_id=subject.user_id, responder_id=responder_id, subject=subject)
            db.session.add(notification)
            db.session.commit()

            return notification
        else:
            raise Exception(f"Unsupported subject type: {type(subject)}")

    def send_notification(self):
        print(f"Sending notification at {self.user.email}")