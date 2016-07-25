# -*- coding: utf-8 -*-

"""
Activity pages views.
"""

from __future__ import unicode_literals

from pyramid import httpexceptions
from pyramid.view import view_config
from sqlalchemy.orm import subqueryload

from h import models
from h.activity import bucketing
from h.api import search as search_lib
from h.api.search import parser
from h.api.search import query
from h.api import storage


@view_config(route_name='activity.search',
             request_method='GET',
             renderer='h:templates/activity/search.html.jinja2')
def search(request):
    if not request.feature('activity_pages'):
        raise httpexceptions.HTTPNotFound()

    results = []
    total = None
    if 'q' in request.params:
        search_query = parser.parse(request.params['q'])

        search_request = search_lib.Search(request)
        search_request.append_filter(query.TopLevelAnnotationsFilter())
        result = search_request.run(search_query)
        total = result.total

        def eager_load_documents(query):
            return query.options(
                subqueryload(models.Annotation.document)
                .subqueryload(models.Document.meta_titles))

        anns = storage.fetch_ordered_annotations(
            request.db, result.annotation_ids,
            query_processor=eager_load_documents)

        timeframes = bucketing.bucket(anns)

        for timeframe in timeframes:
            for document, annotations in timeframe.document_buckets.items():
                results = []
                for annotation in annotations:
                    group = request.db.query(models.Group).filter(
                        models.Group.pubid == annotation.groupid).one_or_none()
                    results.append({'annotation': annotation, 'group': group})
                timeframe.document_buckets[document] = results

    return {
        'q': request.params.get('q', ''),
        'total': total,
        'timeframes': timeframes
    }


def includeme(config):
    config.scan(__name__)
