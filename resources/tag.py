from functools import reduce
from operator import or_

from flask_smorest import abort, Blueprint
from flask.views import MethodView
from sqlalchemy import func, case, desc, not_

from db import db
from models import TagsModel
from schemas import PlainTagSchema, TagSearchSchema

blp = Blueprint('tags', __name__)

@blp.route('/tags')
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
            tags = TagsModel.query
            if tag_data.get('exclude'):
                tags = tags.filter(TagsModel.id.notin_(*tag_data['exclude']))
            return tags.order_by(desc(TagsModel.count)).limit(5).all()

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


        print(search_conditions)
        final_query = TagsModel.query

        if tag_data.get('exclude'):
            if len(tag_data['exclude']) > 1:
                exclude_ids_condition = list(map(lambda id: TagsModel.id == id, tag_data['exclude']))
                final_query = final_query.filter(not_(reduce(or_, exclude_ids_condition)))
            else:
                final_query = final_query.filter(TagsModel.id != tag_data['exclude'][0])


        final_query.filter(reduce(or_, search_conditions)).order_by(desc(final_score)).limit(5)

        return final_query.all()