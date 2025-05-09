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
from schemas import LocationAutocompleteSchema, LocationSearchSchema

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
            },
            "languageCode": "pl"
        }

        request_headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": "AIzaSyAYA8r9HZaGhyJp2JK_ScmYOpspnDe7WQM",
            "X-Goog-FieldMask": "suggestions.placePrediction.placeId,suggestions.placePrediction.structuredFormat.mainText.text,suggestions.placePrediction.structuredFormat.secondaryText.text"
        }

        print(request_data)
        print(request_headers)

        response = requests.post("https://places.googleapis.com/v1/places:autocomplete", headers=request_headers, json=request_data)

        return response.json()

@blp.route('/search-location')
class SearchLocation(MethodView):

    @jwt_required()
    @blp.arguments(LocationSearchSchema(), location='json')
    @blp.response(200)
    def post(self, search_data):
        session = SessionsModel.query.filter_by(user_id=get_jwt_identity()).first()

        if session is None:
            abort(400, message="you cant search location without session you can only start session buy using autocomplete endpoint")

        request_headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": "AIzaSyAYA8r9HZaGhyJp2JK_ScmYOpspnDe7WQM",
            "X-Goog-FieldMask": "displayName,location"
        }

        request_params = {
            "sessionToken": str(session.session_id)
        }

        response = requests.get(f"https://places.googleapis.com/v1/places/{search_data['place_id']}", params=request_params, headers=request_headers)

        if response.status_code == 200:
            db.session.delete(session)
            db.session.commit()

        return response.json()
