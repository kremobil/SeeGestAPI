from operator import or_

from flask_smorest import abort, Blueprint
from flask.views import MethodView
from sqlalchemy import func, case, desc

from db import db
from models import TagsModel
from schemas import PlainTagSchema, TagSearchSchema

blp = Blueprint('tag', __name__)

@blp.route('/tag')
class Tag(MethodView):

    @blp.arguments(PlainTagSchema(), location='json')
    @blp.response(200, PlainTagSchema())
    def post(self, tag_data):
        tag = TagsModel().query.filter_by(name=tag_data['name']).first()
        if tag is not None:
            abort(400, message="Tag already exists")

        tag = TagsModel(**tag_data)

        db.session.add(tag)
        db.session.commit()

        return tag

    @blp.arguments(TagSearchSchema(), location='query')
    @blp.response(200, PlainTagSchema(many=True))
    def get(self, tag_data):
        query = tag_data.get('query', '').strip().lower()
        if not query:
            return TagsModel.query.order_by(desc(TagsModel.count)).limit(10).all()

        # Przygotowujemy wariant zapytania bez myślnika
        query_no_hyphen = query.replace('-', '')

        # Tworzymy wyrażenie CASE do obliczania priorytetu
        priority = case(
            # Dokładne dopasowanie na początku (waga: 10000)
            (TagsModel.name.ilike(f'{query}%'), 10000),
            # Dopasowanie bez myślników na początku (waga: 8000)
            (func.replace(TagsModel.name, '-', '').ilike(f'{query_no_hyphen}%'), 8000),
            # Dopasowanie w środku tekstu (waga: 5000)
            (TagsModel.name.ilike(f'%{query}%'), 5000),
            # Dopasowanie w środku bez myślników (waga: 3000)
            (func.replace(TagsModel.name, '-', '').ilike(f'%{query_no_hyphen}%'), 3000),
            else_=0
        )

        # Obliczamy końcowy score uwzględniający zarówno priorytet jak i popularność
        final_score = priority + func.log(TagsModel.count + 1) * 1000

        # Tworzymy zapytanie z wszystkimi warunkami
        search_conditions = [
            TagsModel.name.ilike(f'{query}%'),
            func.replace(TagsModel.name, '-', '').ilike(f'{query_no_hyphen}%'),
            TagsModel.name.ilike(f'%{query}%'),
            func.replace(TagsModel.name, '-', '').ilike(f'%{query_no_hyphen}%')
        ]

        final_query = (
            TagsModel.query
            .filter(or_(*search_conditions))
            .order_by(desc(final_score))
            .limit(10)
        )

        return final_query.all()