from flask_smorest import Blueprint, abort
from flask.views import MethodView

from db import db
from models import IconsModel
from schemas import IconSchema

blp = Blueprint("icons", __name__)

@blp.route("/icons")
class Icons(MethodView):

    @blp.response(200, IconSchema(many=True))
    def get(self):
        return IconsModel.query.all()

    @blp.arguments(IconSchema())
    @blp.response(201, IconSchema())
    def post(self, icon_data):
        icon = IconsModel(**icon_data)
        db.session.add(icon)
        db.session.commit()

        return icon, 201
