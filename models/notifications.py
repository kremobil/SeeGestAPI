import os

from flask import render_template
from flask_mail import Message
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import generic_relationship
from sqlalchemy import func

from db import db
from mail import mail


class NotificationModel(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('UserModel', back_populates='notifications', foreign_keys=[user_id])
    responder_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    responder = db.relationship('UserModel', foreign_keys=[responder_id])
    is_responder_anonymous = db.Column(db.Boolean)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=func.current_timestamp())

    # relation to dynamic subject Either post or comment
    subject_type = db.Column(db.String(50))
    subject_id = db.Column(db.Integer)
    subject = generic_relationship(subject_type, subject_id)

    @hybrid_property
    def message(self):
        return f"{'Anonimowy Użytkownik' if self.is_responder_anonymous else f'Użytkownik {self.responder.name}'} {'skomentował twój Post' if self.subject_type == 'PostModel' else 'odpowiedział na twój Komentarz'}!"

    @classmethod
    def create_notification(cls, subject: db.Model, responder_id: db.Integer, is_annonymous: bool = False):
        subject_type = subject.__class__.__name__

        if subject_type == 'PostModel':
            notification = cls(user_id=subject.author_id, responder_id=responder_id, subject=subject, is_responder_anonymous=is_annonymous)
            db.session.add(notification)
            db.session.commit()

            return notification
        elif subject_type == 'CommentModel':
            notification = cls(user_id=subject.user_id, responder_id=responder_id, subject=subject, is_responder_anonymous=is_annonymous)
            db.session.add(notification)
            db.session.commit()

            return notification
        else:
            raise Exception(f"Unsupported subject type: {type(subject)}")

    def send_notification(self):
        print(f"Sending notification at {self.user.email}")

        msg = Message(
            subject=f"Masz {'nową opowiedź na twój komentarz' if self.subject_type == 'CommentModel' else 'komentarz pod twoim postem'} na seegest.com",
            recipients=[self.user.email],
        )

        responder_name = "anonimowy użytkownik" if self.is_responder_anonymous else self.responder.name

        if self.subject_type == 'PostModel':
            mail_data = {
                'notification_title': 'Nowy komentarz pod Twoim postem!',
                'notification_message': f'{responder_name.capitalize()} dodał komentarz pod Twoim postem "{self.subject.title}". Sprawdź co napisał!',
                'button_text': 'Zobacz komentarz',
                'action_link': f'https://localhost:5173/posts/{self.subject_id}#comments',
                'settings_link': f"https://localhost:5173/account",
                'user_name': self.user.name,
            }
        else:
            mail_data = {
                'notification_title': 'Ktoś odpowiedział na Twój komentarz!',
                'notification_message': f'{responder_name.capitalize()} odpowiedział na Twój komentarz "{self.subject.content}". Zobacz co napisał!',
                'button_text': 'Zobacz odpowiedź',
                'action_link': f'https://localhost:5173/posts/{self.subject.post_id}#comment-{self.subject_id}',
                'settings_link': f"https://localhost:5173/account",
                'user_name': self.user.name,
            }

        msg.html = render_template("notification.html", title="Notification message", **mail_data)
        msg.attach("logo.png", "image/png", open(os.path.join("static", "mails", "logo.png"), 'rb').read(), 'inline', headers={
            "Content-ID": "<logo>",
        })
        mail.send(msg)