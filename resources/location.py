import json
import os
import uuid

from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_smorest import Blueprint, abort
import requests
from flask.views import MethodView
from flask_cors import cross_origin

from db import db
from models import SessionsModel
from schemas import LocationAutocompleteSchema

blp = Blueprint('location', __name__)

@blp.route('/location-autocomplete')
class LocationAutocomplete(MethodView):
    @jwt_required()
    @blp.arguments(LocationAutocompleteSchema(), location='json')
    @blp.response(200)
    def post(self, search_data):
        session = SessionsModel().query.filter_by(user_id=get_jwt_identity()).first()

        if session is None:
            session = SessionsModel(user_id=get_jwt_identity(), session_id=str(uuid.uuid4()))
            db.session.add(session)
            db.session.commit()

        print(os.environ.get('GOOGLE_API_KEY'))

        request_data = {
            "input": search_data['query'],
            "sessionToken": str(session.session_id),
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": search_data['latitude'],
                        "longitude": search_data['longitude']
                    },
                    "radius": 500.0
                }
            }
        }

        request_headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": "AIzaSyAYA8r9HZaGhyJp2JK_ScmYOpspnDe7WQM"
        }

        print(request_data)
        print(request_headers)

        response = requests.post("https://places.googleapis.com/v1/places:autocomplete", headers=request_headers, json=request_data)

        return response.json()