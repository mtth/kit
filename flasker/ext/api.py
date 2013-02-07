#!/usr/bin/env python

"""API blueprint.

Inspired by Flask-restless.

"""

from flask import abort, Blueprint, jsonify, request
from os.path import abspath, dirname, join
from time import time
from werkzeug.exceptions import HTTPException

class APIError(HTTPException):

  """Thrown when an API call is invalid.

  The error code will sent as error code for the response.

  """

  def __init__(self, code, message):
    self.code = code
    super(APIError, self).__init__(message)

  def __repr__(self):
    return '<APIError %r: %r>' % (self.code, self.message)

class APIManager(object):

  config = {
    'URL_PREFIX': '/api',
  }

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      self.config[k.upper()] = v
    self.Models = {}

  def add_model(self, Model, default_collection_depth=0, default_model_depth=1,
                default_limit=20, max_limit=None, **kwargs):
    self.Models[Model.__name__] = {
      'class': Model,
      'collection_view_options': {
        'default_depth': default_collection_depth,
        'default_limit': default_limit,
        'max_limit': max_limit
      },
      'model_view_options': {
        'default_depth': default_model_depth,
      },
      'route_options': kwargs
    }

  def _create_blueprint(self, project):
    return Blueprint(
      'api',
      project.config['PROJECT']['APP_FOLDER'] + '.api',
      template_folder=abspath(join(dirname(__file__), 'templates', 'api')),
      url_prefix=self.config['URL_PREFIX']
    )

  def _create_model_views(self, data):
    Model = data['class']
    views = [
      ModelView(Model=Model, **data['model_view_options']),
      CollectionView(Model=Model, **data['collection_view_options'])
    ]
    for rel in Model.get_relationships().values():
      if rel.lazy == 'dynamic':
        views.extend([
          ModelView(
            Model=Model, relationship=rel, **data['model_view_options']
          ),
          CollectionView(
            Model=Model, relationship=rel, **data['collection_view_options']
          )
        ])
    for view in views:
      self.blueprint.add_url_rule(
        view.url, view.endpoint, view, **data['route_options']
      )

  def _before_register(self, project):
    self.blueprint = self._create_blueprint(project)
    for data in self.Models.values():
      self._create_model_views(data)
    index_view = IndexView()
    self.blueprint.add_url_rule(
      index_view.url, index_view.endpoint, index_view
    )

  def _after_register(self, project):
    pass

class APIView(object):

  """Base API view."""

  __all__ = []

  Model = None
  relationship = None

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      setattr(self, k, v)
    self.__all__.append(self)

class IndexView(APIView):

  def __call__(self):
    return jsonify({
      'status': 'Welcome',
      'available_endpoints': [v.url for v in self.__all__]
    })

  @property
  def endpoint(self):
    return 'index'
 
  @property
  def url(self):
    return '/'

class CollectionView(APIView):

  params = set(['depth', 'limit', 'offset', 'loaded', 'sort'])
  default_depth = 0
  default_limit = 20
  max_limit = None

  def __call__(self, **kwargs):
    if id is None:
      query = self.Model.query
    else:
      model = self.Model.query.get(kwargs.values())
      if not model:
        return abort(404), 404
      query = getattr(model, self.relationship.key)
    try:
      results = self.process_query(query)
    except APIError as e:
      return jsonify({
        'status': 'Error',
        'request': {
          'base_url': request.base_url,
          'method': request.method,
          'values': request.values
        },
        'content': e.message
      }), e.code
    else:
      return jsonify({
        'status': 'Success',
        'processing_time': results['processing_times'],
        'matches': {
          'total': results['total_matches'],
          'returned': len(results['content'])
        },
        'request': {
          'base_url': request.base_url,
          'method': request.method,
          'values': request.values
        },
        'content': results['content']
      }), 200

  def process_query(self, query):
    Model = query.column_descriptions[0]['type']
    column_names = [c.key for c in Model.get_columns()]
    timer = time()
    processing_times = []
    filters = {}
    for k, v in request.args.items():
      if k in column_names:
        filters[k] = v
      elif not k in self.params:
        raise APIError(400, 'Bad Request')
    try:
      offset = max(0, int(request.args.get('offset', 0)))
      limit = max(0, int(request.args.get('limit', self.default_limit)))
      if self.max_limit:
        limit = min(limit, self.max_limit)
      depth = max(0, int(request.args.get('depth', self.default_depth)))
      loaded = [int(e) for e in request.args.get('loaded', '').split(',') if e]
      sort = request.args.get('sort', '')
    except ValueError as e:
      raise APIError(400, 'Bad Request')
    processing_times.append(('request', time() - timer))
    timer = time()
    for k, v in filters.items():
      query = query.filter(getattr(Model, k) == v)
    total_matches = 10 # query.count()
    processing_times.append(('query', time() - timer))
    timer = time()
    if loaded:
      query = query.filter(~Model.id.in_(loaded))
    if sort:
      attr = sort.strip('-')
      if not attr in column_names:
        raise APIError(400, 'Bad Request')
      if sort[0] == '-':
        query = query.order_by(-getattr(Model, attr))
      else:
        query = query.order_by(getattr(Model, attr))
    if limit:
      query = query.limit(limit)
    return {
      'processing_times': processing_times,
      'total_matches': total_matches,
      'content': [
        e.jsonify(depth=depth)
        for e in query.offset(offset)
      ]
    }

  @property
  def endpoint(self):
    if not self.relationship:
      return '%s_collection_view' % self.Model.__tablename__
    else:
      return '%s_%s_collection_view' % (
        self.Model.__tablename__, self.relationship.key
      )

  @property
  def url(self):
    if not self.relationship:
      return '/%s' % self.Model.__tablename__
    else:
      return '/%s/<id>/%s' % (
        self.Model.__tablename__, self.relationship.key
      )

class ModelView(APIView):

  params = set(['depth'])
  default_depth = 1

  @property
  def endpoint(self):
    if not self.relationship:
      return '%s_model_view' % self.Model.__tablename__
    else:
      return '%s_%s_model_view' % (
        self.Model.__tablename__, self.relationship.key
      )

  @property
  def url(self):
    url = '/%s' % self.Model.__tablename__
    url += ''.join('/<%s>' % n for n in self.Model.get_primary_key_names())
    if self.relationship:
      url += '/%s/<position>' % self.relationship.key
    return url

  def __call__(self, **kwargs):
    position = kwargs.pop('position', None)
    try:
      depth = int(request.args.get('depth', self.default_depth))
      model = self.Model.query.get(kwargs.values())
      if position is not None:
        try:
          pos = int(position) - 1
        except ValueError:
          raise APIError(400, 'Bad Request')
        else:
          if pos >= 0:
            model = getattr(model, self.relationship.key).offset(pos).first()
          else:
            raise APIError(400, 'Bad Request')
      if not model:
        raise APIError(404, 'Not Found')
    except APIError as e:
      return jsonify({
        'status': 'Error',
        'request': {
          'base_url': request.base_url,
          'method': request.method,
          'values': request.values
        },
        'content': e.message
      }), e.code
    else:
      return jsonify(model.jsonify(depth=depth))

