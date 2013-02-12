#!/usr/bin/env python

"""API Extension."""

from flask import Blueprint, jsonify, request
from flask.views import View
from os.path import abspath, dirname, join
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import class_mapper, mapperlib, Query
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.properties import RelationshipProperty
from time import time
from werkzeug.exceptions import HTTPException

from ..project import current_project as pj
from ..util import Cacheable, JSONEncodedDict, _jsonify, Loggable, uncamelcase

class API(object):

  """Main API extension.

  Handles the creation and registration of all API views. Available options:

  * URL_PREFIX
  * ADD_ALL_MODELS
  * DEFAULT_METHODS
  * DEFAULT_ALLOW_PUT_MANY
  * DEFAULT_RELATIONSHIPS
  * DEFAULT_COLLECTION_DEPTH
  * DEFAULT_MODEL_DEPTH
  * DEFAULT_LIMIT
  * MAX_LIMIT

  Models can be added in two ways. Either individually::
    
    api.add_model(Model)

  or globally::

    api.add_all_models()

  Both functions accept the same additional options (cf. their respective doc).

  It also exposes the `authorize` and `validate` decorators.

  Once all the models have been added along with (optionally) the authorize and
  validate functions, the API extension should be registered with the project::

    current_project.register_extension(extension)

  """

  _authorize = None
  _validate = None

  config = {
    'URL_PREFIX': '/api',
    'ADD_ALL_MODELS': False,
    'METHODS': frozenset(['GET', 'POST', 'PUT', 'DELETE']),
    'RELATIONSHIPS': True,
    'DEFAULT_DEPTH': 0,
    'DEFAULT_LIMIT': 20,
    'MAX_LIMIT': None,
  }

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      self.config[k.upper()] = v
    self.Models = {}
    APIView.extension = self

  def add_model(self, Model, **kwargs):
    """Flag a Model to be added.

    TODO: kwargs (relationships, methods...)
    
    Will override any options previously set for that Model.

    If any of the options is ``None``, the default value will be used.

    Relationships can either be ``True`` or a list of relationship keys. In the
    first case, all one to many relationships will have a hook created,
    otherwise only those mentioned in the list.

    It might seem strange that this method doesn't have a columns filter, this
    is for speed and consistency. Columns are defined at the Model level (via
    the json_include and json_exclude attributes), this way:
    
    * jsonify calls do not have to dynamically check which columns to include
    * all endpoints leading to the same Model yield the same columns

    """
    self.Models[Model.__name__] = (Model, kwargs)

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

  def _create_model_views(self, Model, options=None):
    """Creates the views associated with the model.

    Sane defaults are chosen:

    * PUT and DELETE requests are only allowed for endpoints that correspond
      to a single model
    * POST requests are only allowed for endpoints that correspond to
      collections
    * endpoints corresponding to relationships only allow the GET method
      (this choice was made to avoid duplicating features accross endpoints)

    """
    CollectionView.attach_view(Model, None)
    ModelView.attach_view(Model, None)
    for rel in Model.get_relationships():
      if rel.uselist:
        CollectionView.attach_view(Model, rel)
        ModelView.attach_view(Model, rel)

  def _before_register(self, project):
    self.blueprint = Blueprint(
      'api',
      project.config['PROJECT']['APP_FOLDER'] + '.api',
      template_folder=abspath(join(dirname(__file__), 'templates', 'api')),
      url_prefix=self.config['URL_PREFIX']
    )
    if self.config['ADD_ALL_MODELS']:
      Models = [k.class_ for k in mapperlib._mapper_registry]
      for Model in Models:
        if not Model.__name__ in self.Models:
          self.add_model(Model)
    for Model, options in self.Models.values():
      self._create_model_views(Model, options)
    IndexView.attach_view(None, None)

  def _after_register(self, project):
    Model.metadata.create_all(project._engine, checkfirst=True)
    Model.query = _QueryProperty(project)

# SQLAlchemy Model

class _BaseQuery(Query):

  """Base query class.

  From Flask-SQLAlchemy.

  """

  def get_or_404(self, model_id):
    """Like get but aborts with 404 if not found."""
    rv = self.get(model_id)
    if rv is None:
      abort(404)
    return rv

  def first_or_404(self):
    """Like first but aborts with 404 if not found."""
    rv = self.first()
    if rv is None:
      abort(404)
    return rv

class _QueryProperty(object):

  def __init__(self, project):
    self.project = project

  def __get__(self, obj, cls):
    try:
      mapper = class_mapper(cls)
      if mapper:
        return _BaseQuery(mapper, session=self.project.session())
    except UnmappedClassError:
      return None

class ExpandedBase(Cacheable, Loggable):

  """Adding a few features to the declarative base.

  Currently:

  * Automatic table naming
  * Caching
  * Jsonifying
  * Logging

  """

  _cache = Column(JSONEncodedDict)
  _json_depth = -1

  json_exclude = None
  json_include = None
  query = None

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      setattr(self, k, v)

  def __repr__(self):
    primary_keys = ', '.join(
      '%s=%r' % (k, getattr(self, k))
      for k in self.__class__.get_primary_key_names()
    )
    return '<%s (%s)>' % (self.__class__.__name__, primary_keys)

  @declared_attr
  def __tablename__(cls):
    """Automatically create the table name.

    Override this to choose your own tablename (e.g. for single table
    inheritance).

    """
    return '%ss' % uncamelcase(cls.__name__)

  @declared_attr
  def _json_attributes(cls):
    """Create the dictionary of attributes that will be JSONified.

    This is only run once, on class initialization, which makes jsonify calls
    much faster.

    By default, includes all public (don't start with _):

    * properties
    * columns that aren't foreignkeys.
    * joined relationships (where lazy is False)

    """
    rv = set(
        varname for varname in dir(cls)
        if not varname.startswith('_')  # don't show private properties
        if (
          isinstance(getattr(cls, varname), property) 
        ) or (
          isinstance(getattr(cls, varname), Column) and
          not getattr(cls, varname).foreign_keys
        ) or (
          isinstance(getattr(cls, varname), RelationshipProperty) and
          not getattr(cls, varname).lazy == 'dynamic'
        )
      )
    if cls.json_include:
      rv = rv | set(cls.json_include)
    if cls.json_exclude:
      rv = rv - set(cls.json_exclude)
    return list(rv)

  def jsonify(self, depth=0):
    """Special implementation of jsonify for Model objects.
    
    Overrides the basic jsonify method to specialize it for models.

    This function minimizes the number of lookups it does (no dynamic
    type checking on the properties for example) to maximize speed.

    :param depth:
    :type depth: int
    :rtype: dict

    """
    if depth <= self._json_depth:
      # this instance has already been jsonified at a greater or
      # equal depth, so we simply return its key
      return self.get_primary_keys()
    rv = {}
    self._json_depth = depth
    for varname in self._json_attributes:
      try:
        rv[varname] = _jsonify(getattr(self, varname), depth)
      except ValueError as e:
        rv[varname] = e.message
    return rv

  def get_primary_keys(self):
    return dict(
      (k, getattr(self, k))
      for k in self.__class__.get_primary_key_names()
    )

  @classmethod
  def find_or_create(cls, **kwargs):
    instance = self.filter_by(**kwargs).first()
    if instance:
      return instance, False
    instance = cls(**kwargs)
    session = cls.query.db.session
    session.add(instance)
    session.flush()
    return instance, True

  @classmethod
  def get_columns(cls, show_private=False):
    columns = class_mapper(cls).columns
    if not show_private:
      columns = [c for c in columns if not c.key.startswith('_')]
    return columns

  @classmethod
  def get_relationships(cls, show_private=False):
    rels =  class_mapper(cls).relationships.values()
    if not show_private:
      rels = [rel for rel in rels if not rel.key.startswith('_')]
    return rels

  @classmethod
  def get_related_models(cls):
    return [(k, v.mapper.class_) for k, v in cls.get_relationships().items()]

  @classmethod
  def get_primary_key_names(cls):
    return [key.name for key in class_mapper(cls).primary_key]

Model = declarative_base(cls=ExpandedBase)

# Views

class APIError(HTTPException):

  """Thrown when an API call is invalid."""

  def __init__(self, code, content):
    self.code = code
    self.content = content
    super(APIError, self).__init__(content)

  def __repr__(self):
    return '<APIError %r: %r>' % (self.message, self.content)

class APIView(View):

  """Base API view.

  Note that the methods class attribute seems to be passed to the add_url_rule
  function somehow (!).

  A collection can either be:

  * a query (most cases)
  * an instrumented list (in the case of relationships)

  """


  # Flask stuff
  decorators = []
  methods = frozenset(['get', 'post', 'head', 'options',
                       'delete', 'put', 'trace', 'patch'])

  extension = None
  routes = []

  def __init__(self, Model, rel):
    self.Model = Model
    self.rel = rel

  def dispatch_request(self, *args, **kwargs):
    method = getattr(self, request.method.lower(), None)
    if method is None and request.method == 'HEAD':
      method = getattr(self, 'get', None)
    try:
      if method:
        return method(*args, **kwargs)
      else:
        raise APIError(405, 'Method Not Allowed')
    except APIError as e:
      return jsonify({
        'status': e.message,
        'request': {
          'base_url': request.base_url,
          'method': request.method,
          'values': request.values
        },
        'content': e.content
      }), e.code

  @classmethod
  def attach_view(cls, Model, rel):
    route = cls.get_url(Model, rel)
    cls.extension.blueprint.add_url_rule(
      route,
      view_func=cls.as_view(cls.get_endpoint(Model, rel), Model)
    )
    cls.routes.append(route)

  @classmethod
  def get_endpoint(cls, Model, relationship):
    return '%s%s%s' % (
      uncamelcase(cls.__name__),
      '_for_%s' % Model.__tablename__ if Model else '',
      '.%s' % relationship.key if relationship else '',
    )

  @classmethod
  def get_url(cls, Model, relationship):
    url = getattr(cls, 'url', None)
    if not url:
      raise NotImplementedError
    return url

class IndexView(APIView):

  """API 'splash' page with a few helpful keys."""

  url = '/'

  def get(self, **kwargs):
    return jsonify({
      'status': '200 Welcome',
      'available_endpoints': self.routes
    })

class CollectionView(APIView):

  """View for collection endpoints."""

  def get(self, **kwargs):
    params = self.get_params()
    col = self._get_collection(**kwargs)
    if isinstance(col, InstrumentedList):
      results = self._process_list(query, params)
    else:
      results = self._process_query(query, params)
    return jsonify({
      'status': '200 Success',
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

  def post(self, **kwargs):
    if self.is_validated(request.json):
      model = Model(**request.json)
      pj.session.add(model)
      pj.session.commit() # generate an ID
      return jsonify(model.jsonify(depth=params['depth']))
    else:
      raise APIError(400, 'Failed validation')

  def put(self, params, **kwargs):
    parent = self.Model.query.get(kwargs.values())
    if parent:
      models = getattr(model, self.relationship.key)
      if self.is_validated(request.json):
        for model in models:
          for k, v in request.json.items():
            setattr(model, k, v)
        return jsonify(parent.jsonify(depth=params['depth']))
      else:
        raise APIError(400, 'Failed validation')
    else:
      raise APIError(404, 'No resource found for this ID')

  def _get_collection(self, **kwargs):
    """Getting raw query/list."""
    if not kwargs:
      col = self.Model.query
    else:
      model = self.Model.query.get(kwargs.values())
      if not model:
        raise APIError(404, 'No resource found for this ID')
      col = getattr(model, self.rel.key)
    return col

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
      raise APIError(400, 'Invalid parameters')
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
        raise APIError(400, 'Invalid sort parameter')
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

  @classmethod
  def get_url(self, Model, relationship):
    url = '/%s' % Model.__tablename__
    if relationship:
      url += ''.join('/<%s>' % n for n in Model.get_primary_key_names())
      url += '/%s' % relationship.key
    url += '/'
    return url

class ModelView(APIView):

  """View for individual model endpoints."""

  @classmethod
  def get_url(self, Model, relationship):
    url = '/%s' % Model.__tablename__
    url += ''.join('/<%s>' % n for n in Model.get_primary_key_names())
    if relationship:
      url += '/%s/<position>' % relationship.key
    return url

  def get(self, params, **kwargs):
    position = kwargs.pop('position', None)
    depth = int(request.args.get('depth', self.defaults['DEFAULT_MODEL_DEPTH']))
    model = self.Model.query.get(kwargs.values())
    if position is not None:
      try:
        pos = int(position) - 1
      except ValueError:
        raise APIError(400, 'Invalid position index')
      else:
        if pos >= 0:
          query_or_list = getattr(model, self.relationship.key)
          if isinstance(query_or_list, InstrumentedList):
            try:
              model = query_or_list[pos]
            except IndexError:
              model = None
          else:
            model = query_or_list.offset(pos).first()
        else:
          raise APIError(400, 'Invalid position index')
    if not model:
      raise APIError(404, 'No resource at this position')
    return jsonify(model.jsonify(depth=depth))

  def put(self, params, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if model:
      if self.is_validated(request.json):
        for k, v in request.json.items():
          setattr(model, k, v)
        return jsonify(model.jsonify(depth=params['depth']))
      else:
        raise APIError(400, 'Failed validation')
    else:
      raise APIError(404, 'No resource found for this ID')

  def delete(self, params, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if model:
      pj.session.delete(model)
      return jsonify({'status': '200 Success', 'content': 'Resource deleted'})
    else:
      raise APIError(404, 'No resource found for this ID')

# Helper

class RequestParser(object):

  params = frozenset(['filter', 'depth', 'limit', 'sort'])
  sep = ';'

  def __init__(self, allowed_params):
    self.args = request.args
    allowed_params = allowed_params or self.params
    if not set(self.args.keys()) < allowed_params:
      raise APIError(400, 'Invalid parameter found')

  def depth(self):
    return request.args.get('depth', 0, int)

  def offset(self):
    return self.args.get('offset', 0, int)

  def limit(self):
    return self.args.get('limit', 20, int)

  def filters(self):
    raws = self.args.getlist('filter')
    for raw in raws:
      key, op, value = raw.split(self.sep, 3)

  def sorts(self):
    raws = self.args.getlist('sort')
    for raw in raws:
      key, order = raw.split(self.sep)

