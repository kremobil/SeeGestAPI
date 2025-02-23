from datetime import datetime
from math import acos, radians, sin, cos, atan2, sqrt

from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.util import hybridmethod

from db import db

class PostModel(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    icon_id = db.Column(db.Integer, db.ForeignKey('icons.id'), nullable=False)
    icon = db.relationship('IconsModel')
    tags = db.relationship('TagsModel', secondary='posts_tags', back_populates='posts', lazy='dynamic')
    comments = db.relationship('CommentModel', back_populates='post', lazy='dynamic')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('UserModel', back_populates='posts')
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    location = db.Column(db.String, nullable=False)
    is_anonymous = db.Column(db.Boolean, nullable=True, default=False)

    @hybrid_method
    def distance_to(self, lat, lon):
        print(lat, lon, self.latitude, self.longitude)
        radius_km = 6371
        dLat = radians(lat - self.latitude)
        dLon = radians(lon - self.longitude)
        a = sin(dLat/2) * sin(dLat/2) + cos(radians(self.latitude)) * cos(radians(lat)) * sin(dLon/2) * sin(dLon/2)
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return radius_km * c


    @distance_to.expression
    def distance_to(cls, lat, lon):
        # Implementacja SQL wzoru haversine
        radius = 6371  # km

        lat = func.radians(lat)
        lon = func.radians(lon)
        lat1 = func.radians(cls.latitude)
        lon1 = func.radians(cls.longitude)

        dlon = lon - lon1
        dlat = lat - lat1

        a = func.pow(func.sin(dlat / 2), 2) + \
            func.cos(lat1) * func.cos(lat) * \
            func.pow(func.sin(dlon / 2), 2)

        c = 2 * func.asin(func.sqrt(a))

        return radius * c