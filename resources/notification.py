from datetime import datetime

from flask import jsonify
from flask.views import MethodView
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import abort, Blueprint

from db import db
from models import NotificationModel
from schemas import NotificationSchema

blp = Blueprint("notification", __name__)

@blp.route("/notifications")
class Notifications(MethodView):

    # TODO: Delete at production
    @blp.response(200, NotificationSchema(many=True))
    def get(self):
        return NotificationModel.query.all()

    @jwt_required()
    @blp.response(200)
    def delete(self):
        notifications = NotificationModel.query.filter_by(user_id=get_jwt_identity()).all()
        for notification in notifications:
            db.session.delete(notification)
        db.session.commit()

        return {
            "message": "all notifications deleted",
        }

@blp.route("/notifications/<int:id>")
class Notification(MethodView):

    @jwt_required()
    @blp.response(200)
    def delete(self, notification_id):
        notification = NotificationModel.query.get_or_404(notification_id)
        db.session.delete(notification)
        db.session.commit()

        return {
            "message": "Notification successfully deleted",
        }

@blp.route("/my-notifications")
class MyNotifications(MethodView):
    @jwt_required()
    @blp.response(200, NotificationSchema(many=True))
    def get(self):
        notifications = NotificationModel.query.filter_by(user_id=get_jwt_identity()).all()
        response = NotificationSchema(many=True).dump(notifications)
        for notification in notifications:
            notification.is_read = True

        db.session.commit()

        return jsonify(response)