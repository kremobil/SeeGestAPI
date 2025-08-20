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
from schemas import LocationAutocompleteSchema, LocationSearchSchema, DecodeLocationSchema

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
            "X-Goog-Api-Key": "SECRET_REDACTED", #TODO: Replace with enviorment variable
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
            "X-Goog-Api-Key": "SECRET_REDACTED",
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

@blp.route('/decode-location')
class DecodeLocation(MethodView):
    @jwt_required()
    @blp.response(200)
    @blp.arguments(DecodeLocationSchema(), location='json')
    def post(self, location_data):
        request_params = {
            "key": "SECRET_REDACTED",
            "latlng": f"{location_data['latitude']},{location_data['longitude']}",
            "language": "pl"
        }

        response = requests.get(f"https://maps.googleapis.com/maps/api/geocode/json",
                                params=request_params)

        return parse_geocoding_response(response.json())


def parse_geocoding_response(geocoding_response: dict) -> str:
    """
    Przetwarza odpowiedź z Google Geocoding API i zwraca czytelny opis lokalizacji.

    Args:
        geocoding_response: Dict z odpowiedzią API

    Returns:
        str: Sformatowany adres w formie np. "Grunwaldzka 30, Bydgoszcz"
    """

    if not geocoding_response.get('results'):
        return "Nieznana lokalizacja"

    # Funkcja pomocnicza do wyciągania komponentów
    def get_component(components, types_to_find):
        """Znajduje komponent po typie"""
        for component in components:
            if any(t in component.get('types', []) for t in types_to_find):
                return component.get('long_name')
        return None

    # Funkcja do oceny jakości wyniku
    def score_result(result):
        """Przypisuje punktację do wyniku na podstawie różnych kryteriów"""
        score = 0
        types = result.get('types', [])
        location_type = result.get('geometry', {}).get('location_type', '')

        # Priorytet dla typów (od najlepszych)
        if 'establishment' in types or 'point_of_interest' in types:
            score += 100
        elif 'street_address' in types:
            score += 80
        elif 'route' in types:
            score += 60
        elif 'neighborhood' in types:
            score += 40
        elif 'postal_code' in types:
            score += 20

        # Bonus za dokładność lokalizacji
        if location_type == 'ROOFTOP':
            score += 50
        elif location_type == 'RANGE_INTERPOLATED':
            score += 30
        elif location_type == 'GEOMETRIC_CENTER':
            score += 10

        # Penalty dla dróg krajowych/wojewódzkich
        components = result.get('address_components', [])
        route = get_component(components, ['route'])
        if route and any(prefix in route for prefix in ['DK', 'DW', 'Droga Krajowa', 'Droga Wojewódzka']):
            score -= 30

        return score

    # Sortuj wyniki według punktacji
    results_with_scores = [(r, score_result(r)) for r in geocoding_response['results'][:5]]
    results_with_scores.sort(key=lambda x: x[1], reverse=True)

    # Wybierz najlepszy wynik
    best_result = results_with_scores[0][0]
    components = best_result.get('address_components', [])
    types = best_result.get('types', [])

    # Wyciągnij komponenty
    establishment = get_component(components, ['establishment', 'point_of_interest'])
    street_number = get_component(components, ['street_number'])
    route = get_component(components, ['route'])
    neighborhood = get_component(components, ['neighborhood'])
    locality = get_component(components, ['locality'])
    postal_code = get_component(components, ['postal_code'])

    # Formatowanie w zależności od typu i dostępnych komponentów
    def format_location():
        parts = []

        # Jeśli to konkretne miejsce (establishment/POI)
        if 'establishment' in types or 'point_of_interest' in types:
            if establishment:
                parts.append(establishment)
            elif route and street_number:
                parts.append(f"{route} {street_number}")
            elif route:
                parts.append(route)

        # Jeśli to adres ulicowy
        elif 'street_address' in types:
            if route and street_number:
                # Sprawdź czy to nie droga krajowa/wojewódzka
                if any(prefix in route for prefix in ['DK', 'DW', 'Droga Krajowa']):
                    # Dla dróg krajowych użyj formatted_address lub szukaj alternatywy
                    if len(results_with_scores) > 1:
                        # Spróbuj znaleźć lepszy wynik (nie-DK/DW)
                        for alt_result, _ in results_with_scores[1:]:
                            alt_route = get_component(
                                alt_result.get('address_components', []),
                                ['route']
                            )
                            if alt_route and not any(p in alt_route for p in ['DK', 'DW']):
                                parts.append(f"{alt_route} {street_number}")
                                break
                        else:
                            # Jeśli nie ma alternatywy, użyj skróconej formy
                            parts.append(f"{route} {street_number}")
                else:
                    parts.append(f"{route} {street_number}")
            elif route:
                parts.append(route)

        # Jeśli to tylko droga
        elif 'route' in types:
            if route:
                parts.append(route)

        # Jeśli to dzielnica
        elif 'neighborhood' in types:
            if neighborhood:
                parts.append(neighborhood)

        # Dodaj miasto jeśli istnieje
        if locality and locality not in parts:
            parts.append(locality)

        return ", ".join(parts) if parts else None

    # Sformatuj lokalizację
    formatted = format_location()

    # Fallback do formatted_address jeśli formatowanie nie powiodło się
    if not formatted:
        # Weź pierwsze 2 elementy formatted_address
        formatted_addr = best_result.get('formatted_address', '')
        parts = formatted_addr.split(',')[:2]
        formatted = ", ".join(p.strip() for p in parts)

    return formatted
