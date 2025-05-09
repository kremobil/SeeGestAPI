from db import db

class IconsModel(db.Model):
    __tablename__ = 'icons'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'))
    file = db.relationship('FileModel')