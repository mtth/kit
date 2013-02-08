#!/usr/bin/env python

"""API blueprint.

Inspired by Flask-restless.

"""

from flask import abort, Blueprint, jsonify, request
from os.path import abspath, dirname, join
from sqlalchemy.orm.collections import InstrumentedList
from time import time
from werkzeug.exceptions import HTTPException

from ..project import current_project

db = current_project.db


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

  _authorize = None
  _validate = None

  config = {
    'URL_PREFIX': '/api',
    'DEFAULT_COLLECTION_DEPTH': 0,
    'DEFAULT_MODEL_DEPTH': 1,
    'DEFAULT_LIMIT': 20,
    'MAX_LIMIT': None,
  }

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      self.config[k.upper()] = v
    self.Models = {}

  def add_model(self, Model, relationships=True,
                methods=frozenset(['GET', 'POST', 'PUT', 'DELETE'])):
    """Flag a Model to be added.

    relationships can either be ``True`` or a list of relationship keys. In the
    first case, all one to many relationships will have a hook created,
    otherwise only those mentioned in the list.

    """
    self.Models[Model.__name__] = {
      'Model': Model,
      'methods': methods,
      'relationships': relationships,
    }

  def authorize(self, func):
    """Decorator to set the authorizer function.

    The authorizer is passed three arguments:
    
    * the model class
    * the relationship (or ``None``)
    * the request method 

    The third argument is for convenience (the full request object can be 
    accessed as usual).

    If the function returns a truthful value, the request will proceed.
    Otherwise a 403 exception is raised.
    
    """
    self._authorize = func

  def validate(self, func):
    """Decorator to set the validate function, called on POST and PUT.

    The validator will be passed two arguments:

    * the model class
    * the request json
    * the request method

    If the function returns a truthful value, the request will proceed.
    Otherwise a 400 exception is raised.

    """
    self._validate = func

  def _create_model_views(self, Model, relationships, methods):
    """Creates the views associated with the model.

    Sane defaults are chosen.

    """
    views = []
    methods = set(methods)
    model_methods = methods & set(['GET', 'PUT', 'DELETE'])
    if model_methods:
      views.append(ModelView(Model=Model, methods=model_methods))
    collection_methods = methods & set(['GET', 'POST'])
    if collection_methods:
      views.append(CollectionView(Model=Model, methods=collection_methods))
    rels = relationships or []
    rel_methods = set(['GET']) & methods
    if rel_methods:
      for rel in Model.get_relationships().values():
        if (rels is True or rel.key in rels) and rel.uselist:
          views.extend([
            ModelView(Model=Model, relationship=rel, methods=rel_methods),
            CollectionView(Model=Model, relationship=rel, methods=rel_methods)
          ])
    for view in views:
      self.blueprint.add_url_rule(view.url, view.endpoint, view)

  def _before_register(self, project):
    self.blueprint = Blueprint(
      'api',
      project.config['PROJECT']['APP_FOLDER'] + '.api',
      template_folder=abspath(join(dirname(__file__), 'templates', 'api')),
      url_prefix=self.config['URL_PREFIX']
    )
    for data in self.Models.values():
      self._create_model_views(**data)
    index_view = IndexView()
    self.blueprint.add_url_rule(
      index_view.url, index_view.endpoint, index_view
    )

  def _after_register(self, project):
    """Give access to defaults and authorizer to views."""
    APIView._manager = self


class APIView(object):

  """Base API view.

  Note that the methods class attribute seems to be passed to the add_url_rule
  function somehow (!).
  
  """

  __all__ = []

  _manager = None

  Model = None
  relationship = None
  methods = set()
  params = set()

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      setattr(self, k, v)
    self.__all__.append(self)

  def __call__(self, **kwargs):
    """Redirects to corresponding request handler."""
    try:
      if not self.is_authorized():
        raise APIError(403, 'Forbidden')
      if request.method in self.methods:
        params = self._parse_params()
        return getattr(self, request.method.lower())(params, **kwargs)
      else:
        raise APIError(405, 'Method Not Allowed')
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

  @property
  def authorized_methods(self):
    return set(
      method for method in self.methods 
      if self._manager._authorize(self.Model, self.relationship, method)
    )

  @property
  def defaults(self):
    return self._manager.config

  def is_validated(self, json):
    """Validate changes."""
    if not self._manager._validate:
      return True
    return self._mananager._validate(self.Model, json, request.method)

  def is_authorized(self):
    if not self._manager._authorize:
      return True
    return self._manager._authorize(
      self.Model, self.relationship, request.method
    )

  def _parse_params(self):
    return request.args

class IndexView(APIView):

  methods = set(['GET'])

  @property
  def endpoint(self):
    return 'index'
 
  @property
  def url(self):
    return '/'

  def get(self, params, **kwargs):
    return jsonify({
      'status': 'Welcome',
      'available_endpoints': [
        '%s (%s)' % (v.url, ', '.join(v.authorized_methods))
        for v in self.__all__
        if v.authorized_methods
      ]
    })


class CollectionView(APIView):

  params = set(['depth', 'limit', 'offset', 'loaded', 'sort'])

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
    url = '/%s' % self.Model.__tablename__
    if self.relationship:
      url += ''.join('/<%s>' % n for n in self.Model.get_primary_key_names())
      url += '/%s' % self.relationship.key
    url += '/'
    return url

  def get(self, params, **kwargs):
    if not kwargs:
      query = self.Model.query
    else:
      model = self.Model.query.get(kwargs.values())
      if not model:
        raise APIError(404, 'Not Found')
      query = getattr(model, self.relationship.key)
    if isinstance(query, InstrumentedList):
      results = self._process_list(query, params)
    else:
      results = self._process_query(query, params)
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

  def post(self, params, **kwargs):
    if self.is_validated(request.json):
      model = Model(**request.json)
      db.session.add(model)
    else:
      raise APIError(400, 'Bad Request')

  def _process_list(self, lst, params):
    return {
      'processing_times': [],
      'total_matches': len(lst),
      'content': [e.jsonify(self.defaults['DEFAULT_COLLECTION_DEPTH']) for e in lst]
    }

  def _process_query(self, query, params):
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
      limit = max(0, int(
        request.args.get('limit', self.defaults['DEFAULT_LIMIT'])
      ))
      if self.defaults['MAX_LIMIT']:
        limit = min(limit, self.defaults['MAX_LIMIT'])
      depth = max(0, int(
        request.args.get('depth', self.defaults['DEFAULT_COLLECTION_DEPTH'])
      ))
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

class ModelView(APIView):

  params = set(['depth'])

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

  def get(self, params, **kwargs):
    position = kwargs.pop('position', None)
    depth = int(request.args.get('depth', self.defaults['DEFAULT_MODEL_DEPTH']))
    model = self.Model.query.get(kwargs.values())
    if position is not None:
      try:
        pos = int(position) - 1
      except ValueError:
        raise APIError(400, 'Bad Request')
      else:
        if pos >= 0:
          query_or_list = getattr(model, self.relationship.key)
          if isinstance(query_or_list, InstrumentedList):
            model = query_or_list[pos]
          else:
            model = query_or_list.offset(pos).first()
        else:
          raise APIError(400, 'Bad Request')
    if not model:
      raise APIError(404, 'Not Found')
    return jsonify(model.jsonify(depth=depth))

  def put(self, params, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if self.is_validated(request.json):
      for k, v in request.json.items():
        setattr(model, k, v)
    else:
      raise APIError(400, 'Bad Request')

  def delete(self, params, **kwargs):
    model = self.Model.query.get(kwargs.values())
    db.session.delete(model)

