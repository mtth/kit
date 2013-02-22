#!/usr/bin/env python

"""API Extension.

Models can be added in two ways. Either individually::
  
  api.add_model(Model)

or globally::

  api.add_all_models()

Both functions accept the same additional options (cf. ``add_all_models``)

It also exposes the `authorize` and `validate` decorators.

Once all the models have been added along with (optionally) the authorize and
validate functions, the API extension should be registered with the project::

  current_project.register_extension(extension)

Next steps:

To configure further the views corresponding to each model, you can access
the ``__view__`` attribute and insert your custom API views there.

"""

from flask import Blueprint, jsonify, request
from os.path import abspath, dirname, join
from sqlalchemy import Column, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import class_mapper, mapperlib, Query
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.dynamic import AppenderQuery
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty
from time import time
from werkzeug.exceptions import HTTPException

from ..project import current_project as pj
from ..util import (Cacheable, _jsonify, JSONDepthExceededError,
  JSONEncodedDict, Loggable, uncamelcase)


class APIError(HTTPException):

  """Thrown when an API call is invalid.

  The following error codes can occur:

  * ``400 Bad Request`` if the request is badly formulated (wrong query
    parameters, invalid form data, etc.)
  * ``403 Forbidden`` if the request is not authorized by the server
  * ``404 Not Found`` if the request refers to a non-existent resource
  
  """

  def __init__(self, code, content):
    self.code = code
    self.content = content
    super(APIError, self).__init__(content)

  def __repr__(self):
    return '<APIError %r: %r>' % (self.message, self.content)

class API(object):

  """Main API extension.

  Handles the creation and registration of all API views. The following
  configuration options are available:

  * ``URL_PREFIX`` the blueprint URL prefix (defaults to ``/api``)
  * ``DEFAULT_DEPTH`` the default depth models are jsonified to. ``0`` yields 
    an empty dictionary (defaults to ``1``).
  * ``DEFAULT_LIMIT`` the default number of results returned per query 
    (defaults to ``20``)
  * ``MAX_LIMIT`` the maximum number of results returned by a query. ``0`` 
    means no limit (defaults to ``0``).
  * ``EXPAND`` if ``True``, same model data will be repeated in the response
    if the model is encountered multiple times, otherwise only the key will
    be returned. This can be very useful for efficiency when used with a 
    client-side library such as Backbone-Relational (defaults to ``True``).

  These can either be passed to the constructor (parameter names are not case
  sensitive)::

    api = API(url_prefix='/my_api', max_limit=10)

  Or they can be stored in the main project configuration file and passed on
  when registering the extension with the ``config_section`` argument::

    current_project.register_extension(api, config_section='API')

  """

  _authorize = None
  _validate = None

  config = {
    'URL_PREFIX': '/api',
    'DEFAULT_DEPTH': 1,
    'DEFAULT_LIMIT': 20,
    'MAX_LIMIT': 0,
    'EXPAND': True,
  }

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      self.config[k.upper()] = v
    APIView.__extension__ = self
    self.Models = {}

  def authorize(self, func):
    """Decorator to set the authorization function.

    :param func: an authorization function. It will be called everytime a new
      request comes in and is passed 2 arguments:
    
      * the endpoint
      * the request method

      If the function returns a truthful value, the request will proceed.
      Otherwise a 403 exception is raised.
    
    """
    self._authorize = func

  def validate(self, func):
    """Decorator to set the validate function, called on POST, PUT and PATCH.

    The validator will be passed two arguments:

    * the model class
    * the request json

    If the function returns a truthful value, the request will proceed.
    Otherwise a 400 exception is raised.

    """
    self._validate = func

  def add_model(self, Model, relationships=True, methods=True):
    """Flag a Model to be added.

    :param Model: the ``Model`` subclass to be exposed.
    :param relationships: whether or not to create subroutes for the model's
      lazy and dynamic relationships. This parameter can take the following
      values:

      * ``True`` to create routes for all 
      * ``False`` to create none
      * a list of relationship keys to create routes for

    :param methods: which request methods to allow. Can take the following
      values:

      * ``True`` to allow all
      * a list of methods to allow
    
    Calling this function multiple times will override any options previously 
    set for the Model.

    ..note::
      
      Only relationships with ``lazy`` set to ``'dynamic'``, ``'select'`` or
      ``True`` can have subroutes. All eagerly loaded relationships are simply
      available directly on the model.

    """
    self.Models[Model.__name__] = (Model, {
      'relationships': relationships,
      'methods': methods
    })

  def add_all_models(self, **kwargs):
    """Convenience method to add all registered models.
    
    This method accepts same arguments as ``add_model``, which will be passed
    to all models.
    
    Remember that calling ``add_model`` overwrites previous options, so it
    is possible to add all models and individually changing the options for
    each by calling the ``add_model`` method for a few models afterwards.
    
    """
    for model_class in [k.class_ for k in mapperlib._mapper_registry]:
      if not model_class.__name__ in self.Models:
        self.add_model(model_class, **kwargs)

  def _create_model_views(self, Model, options):
    view = Model.__view__
    relationships = options.pop('relationships')
    if 'collection' in view: view['collection'].attach_view(Model, **options)
    if 'model' in view: view['model'].attach_view(Model, **options)
    if relationships == True:
      rels = Model.get_relationships()
    elif relationships == False:
      rels = []
    else:
      rels = filter(
        lambda r: r.key in relationships,
        Model.get_relationships()
      )
    for rel in rels:
      if rel.lazy == 'dynamic' and rel.uselist:
        if 'relationship_model' in view:
          view['relationship_model'].attach_view(rel, **options)
        if 'dynamic_relationship' in view:
          view['dynamic_relationship'].attach_view(rel, **options)
      elif rel.lazy in [True, 'select'] and rel.uselist:
        if 'relationship_model' in view:
          view['relationship_model'].attach_view(rel, **options)
        if 'lazy_relationship' in view:
          view['lazy_relationship'].attach_view(rel, **options)

  def _before_register(self, project):
    self.blueprint = Blueprint(
      'api',
      project.config['PROJECT']['APP_FOLDER'] + '.api',
      template_folder=abspath(join(dirname(__file__), 'templates', 'api')),
      url_prefix=self.config['URL_PREFIX']
    )
    for model_class, options in self.Models.values():
      self._create_model_views(model_class, options)
    IndexView.attach_view()

  def _after_register(self, project):
    Model.metadata.create_all(project._engine, checkfirst=True)
    Model.query = _QueryProperty(project)

# Views

class APIView(object):

  """Base API view.

  Subclass this to implement your own.
  
  """

  __all__ = []
  __extension__ = None

  # Flask stuff
  decorators = []
  methods = frozenset(['GET', 'POST', 'HEAD', 'OPTIONS',
                       'DELETE', 'PUT', 'TRACE', 'PATCH'])

  # these control which requests are allowed:
  # the default behavior is to allow all request methods that have a 
  # corresponding method implemented but this can be further restricted
  # with the ``methods`` kwarg of ``add_model``, reflected here
  allowed_methods = frozenset()
  # which url query parameters are allowed by the parser
  allowed_request_keys = frozenset()

  def __call__(self, *args, **kwargs):
    method = getattr(self, request.method.lower(), None)
    if method is None and request.method == 'HEAD':
      method = getattr(self, 'get', None)
    try:
      if not method or request.method not in self.allowed_methods:
        raise APIError(405, 'Method Not Allowed')
      elif not self._is_authorized():
        raise APIError(403, 'Not authorized')
      else:
        parser = Parser(self.allowed_request_keys)
        return method(parser, *args, **kwargs)
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

  def get_endpoint(self):
    """Returns the endpoint for use in the blueprint.

    These should be unique accross all your API views.
    
    """
    return uncamelcase(self.__class__.__name__)

  def get_rule(self):
    """Returns the URL route for the view.

    Routes should be unique (duh).

    """
    return self.url

  def _get_available_methods(self):
    endpoint = self.get_endpoint()
    return [
      m for m in set(m.upper() for m in dir(self)) & self.allowed_methods
      if self._is_authorized(m.upper())
    ]

  def _is_authorized(self, method=None):
    method = method or request.method
    authorize = self.__extension__._authorize
    if not authorize or authorize(self.get_endpoint(), method):
      return True
    return False

  def _is_valid(self, Model, json):
    validate = self.__extension__._validate
    if not validate or validate(Model, json):
      return True
    return False

  @classmethod
  def attach_view(cls, *view_args, **view_kwargs):
    """Create and attach a view to the blueprint.

    New views should be created with this method otherwise the extension will
    be unaware of them.
    
    """
    view = cls(*view_args)
    methods = view_kwargs.get('methods', True)
    if methods == True:
      view.allowed_methods = cls.methods
    else:
      view.allowed_methods = frozenset(methods)
    cls.__extension__.blueprint.add_url_rule(
      rule=view.get_rule(),
      endpoint=view.get_endpoint(),
      view_func=view,
      methods=cls.methods
    )
    cls.__all__.append(view)

class CollectionView(APIView):

  """Default view for collection endpoints."""

  allowed_request_keys = frozenset(['depth', 'limit', 'offset', 'filter', 
                                    'sort', 'expand'])

  def __init__(self, Model):
    self.Model = Model

  def get_endpoint(self):
    return 'collection_view_for_%s' % self.Model.__tablename__

  def get_rule(self):
    return '/%s' % self.Model.__tablename__

  def get(self, parser, **kwargs):
    timers = {}
    filtered_query = parser.filter_and_sort(self.Model.query)
    now = time()
    count = parser.filter_and_sort(
      self.Model.query.get_count_query(), False
    ).one()[0]
    timers['count'] = time() - now
    now = time()
    content = [
      e.jsonify(**parser.get_jsonify_kwargs())
      for e in parser.offset_and_limit(filtered_query)
    ]
    timers['jsonification'] = time() - now
    return jsonify({
      'status': '200 Success',
      'processing_time': timers,
      'matches': {
        'total': count,
        'returned': len(content),
      },
      'request': {
        'base_url': request.base_url,
        'method': request.method,
        'values': request.values
      },
      'content': content
    }), 200

  def post(self, parser, **kwargs):
    if self._is_valid(self.Model, request.json):
      model = self.Model(**request.json)
      pj.session.add(model)
      pj.session.commit() # generate an ID
      return jsonify(model.jsonify(**parser.get_jsonify_kwargs()))
    else:
      raise APIError(400, 'Failed validation')

class ModelView(APIView):

  """Default view for individual model endpoints."""

  allowed_request_keys = frozenset(['depth', 'expand'])

  def __init__(self, Model):
    self.Model = Model

  def get_endpoint(self):
    return 'model_view_for_%s' % self.Model.__tablename__

  def get_rule(self):
    url = '/%s' % self.Model.__tablename__
    url += ''.join('/<%s>' % n for n in self.Model.get_primary_key_names())
    return url

  def get(self, parser, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if not model:
      raise APIError(404, 'No resource found')
    return jsonify(model.jsonify(**parser.get_jsonify_kwargs()))

  def put(self, parser, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if model:
      if self._is_valid(model.__class__, request.json):
        for k, v in request.json.items():
          setattr(model, k, v)
        return jsonify(model.jsonify(**parser.get_jsonify_kwargs()))
      else:
        raise APIError(400, 'Failed validation')
    else:
      raise APIError(404, 'No resource found for this ID')

  def patch(self, parser, **kwargs):
    pass

  def delete(self, parser, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if model:
      pj.session.delete(model)
      return jsonify({'status': '200 Success', 'content': 'Resource deleted'})
    else:
      raise APIError(404, 'No resource found for this ID')

class RelationshipView(APIView):

  """Not an actual view, meant to be subclassed."""

  def __init__(self, rel):
    self.rel = rel

  @property
  def Model(self):
    return self.rel.mapper.class_

  @property
  def parent_Model(self):
    return self.rel.parent.class_

  def get_endpoint(self):
    return 'relationship_view_for_%s_%s' % (
      uncamelcase(self.parent_Model.__name__),
      self.rel.key
    )

  def get_rule(self):
    url = '/%s' % self.parent_Model.__tablename__
    url += ''.join(
      '/<%s>' % n for n in self.parent_Model.get_primary_key_names()
    )
    url += '/%s' % self.rel.key
    return url

  def get_collection(self, **kwargs):
    parent_model = self.parent_Model.query.get(kwargs.values())
    if not parent_model:
      raise APIError(404, 'No resource found')
    return getattr(parent_model, self.rel.key)

class DynamicRelationshipView(RelationshipView):

  """Default view for dynamic relationships."""

  allowed_request_keys = frozenset(['depth', 'limit', 'offset', 'filter',
                                    'sort', 'expand'])

  def get(self, parser, **kwargs):
    query = parser.filter_and_sort(self.get_collection(**kwargs))
    timers = {}
    now = time()
    count = query.count()
    timers['count'] = time() - now
    now = time()
    content = [
      e.jsonify(**parser.get_jsonify_kwargs())
      for e in parser.offset_and_limit(query)
    ]
    timers['jsonification'] = time() - now
    return jsonify({
      'status': '200 Success',
      'processing_time': timers,
      'matches': {
        'total': count,
        'returned': len(content),
      },
      'request': {
        'base_url': request.base_url,
        'method': request.method,
        'values': request.values
      },
      'content': content
    }), 200

class LazyRelationshipView(RelationshipView):

  """Default view for lazy relationships."""

  allowed_request_keys = frozenset(['depth', 'expand'])

  def get(self, parser, **kwargs):
    timers = {}
    now = time()
    content = [
      e.jsonify(**parser.get_jsonify_kwargs())
      for e in self.get_collection(**kwargs)
    ]
    count = len(content)
    timers['jsonification'] = time() - now
    return jsonify({
      'status': '200 Success',
      'processing_time': timers,
      'matches': {
        'total': count,
        'returned': count,
      },
      'request': {
        'base_url': request.base_url,
        'method': request.method,
        'values': request.values
      },
      'content': content
    }), 200

class RelationshipModelView(RelationshipView):

  """Default view for relationship models."""

  allowed_request_keys = frozenset(['depth', 'expand'])

  def get_endpoint(self):
    return 'relationship_model_view_for_%s_%s' % (
      self.parent_Model.__name__,
      self.rel.key
    )

  def get_rule(self):
    url = '/%s' % self.parent_Model.__tablename__
    url += ''.join(
      '/<%s>' % n for n in self.parent_Model.get_primary_key_names()
    )
    url += '/%s/<key>' % self.rel.key
    return url

  def get(self, parser, **kwargs):
    key = kwargs.pop('key')
    collection = self.get_collection(**kwargs)
    if isinstance(collection, (InstrumentedList, AppenderQuery)):
      try:
        pos = int(key) - 1
      except ValueError:
        raise APIError(400, 'Invalid key')
      else:
        if pos >= 0:
          if isinstance(collection, InstrumentedList):
            try:
              model = collection[pos]
            except IndexError:
              model = None
          else:
            model = collection.offset(pos).first()
        else:
          raise APIError(400, 'Invalid position index')
    # TODO: support attribute mapped collections
    if not model:
      raise APIError(404, 'No resource found')
    return jsonify(model.jsonify(**parser.get_jsonify_kwargs()))

  def put(self, parser, **kwargs):
    pass

class IndexView(APIView):

  """API splash page with a few helpful keys."""

  url = '/'

  def get(self, params, **kwargs):
    return jsonify({
      'status': '200 Welcome',
      'available_endpoints': [
        '%s (%s)' % (
          view.get_rule(),
          ', '.join(m.upper() for m in view._get_available_methods()))
        for view in self.__all__
        if view._get_available_methods()
      ]
    })

# SQLAlchemy Model

def get_model_classes_from_query(query):
  return [
    d['expr'].class_
    for d in query.column_descriptions
    if isinstance(d['expr'], Mapper)
  ]

class _BaseQuery(Query):

  """Base query class.

  The first two methods are copied from Flask-SQLAlchemy.

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

  def get_count_query(self):
    """Get correspondint count query.

    This should be used for fast counts. Apply filters to it and apply the
    method ``one()`` to bypass the use of subqueries (which are highly
    inefficient in MySQL).
    
    """
    models = self.get_models()

    # _BaseQuery objects should only ever have one model
    assert len(models) == 1, '%s models found for %s' % (len(models), self)

    Model = models[0]
    query = pj.session.query(func.count(Model)).select_from(Model)
    return query

  def get_models(self):
    return get_model_classes_from_query(self)

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

  __view__ = {
    'model': ModelView,
    'collection': CollectionView,
    'dynamic_relationship': DynamicRelationshipView,
    'lazy_relationship': LazyRelationshipView,
    'relationship_model': RelationshipModelView
  }

  _cache = Column(JSONEncodedDict)
  _json_depth = 0

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
  def __json__(cls):
    """Varnames that get JSONified.

    Doesn't emit any additional queries!

    """
    return list(
      varname
      for varname in dir(cls)
      if not varname.startswith('_')  # don't show private properties
      if (
        isinstance(getattr(cls, varname), property) 
      ) or (
        isinstance(getattr(cls, varname), InstrumentedAttribute) and
        isinstance(getattr(cls, varname).property, ColumnProperty)
      ) or (
        isinstance(getattr(cls, varname), InstrumentedAttribute) and
        isinstance(getattr(cls, varname).property, RelationshipProperty)
        and (
          getattr(cls, varname).property.lazy in [False, 'joined', 'immediate']
        )
      )
    )

  @declared_attr
  def __tablename__(cls):
    """Automatically create the table name.

    Override this to choose your own tablename (e.g. for single table
    inheritance).

    """
    return '%ss' % uncamelcase(cls.__name__)

  def jsonify(self, depth=1, expand=True):
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
      # equal depth, so we simply return its key (only used if expand is False)
      return self.get_primary_keys()
    if not expand:
      self._json_depth = depth
    rv = {}
    for varname in self.__json__:
      try:
        rv[varname] = _jsonify(getattr(self, varname), depth - 1, expand)
      except ValueError as e:
        rv[varname] = e.message
      except JSONDepthExceededError:
        pass
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
  def get_primary_key_names(cls):
    return [key.name for key in class_mapper(cls).primary_key]

  @classmethod
  def get_relationships(cls, show_private=False):
    rels =  class_mapper(cls).relationships.values()
    if not show_private:
      rels = [rel for rel in rels if not rel.key.startswith('_')]
    return rels

  @classmethod
  def get_related_models(cls, show_private=False):
    return [
      (r.key, r.mapper.class_)
      for r in cls.get_relationships(show_private)
    ]

Model = declarative_base(cls=ExpandedBase)

# Helper

class Parser(object):

  """The request parameter parser.
  
  """

  sep = ';' # the separator used for filters and sorts

  def __init__(self, allowed_keys):
    self.defaults = APIView.__extension__.config
    self.args = request.args
    self.keys = set(self.args.keys())
    if not self.keys <= set(allowed_keys):
      raise APIError(400, 'Invalid parameters found: %s not in %s' % (
        list(self.keys), list(allowed_keys)
       ))

  def get_jsonify_kwargs(self):
    return {
      'depth': self.args.get('depth', self.defaults['DEFAULT_DEPTH'], int),
      'expand': self.args.get('expand', self.defaults['EXPAND'], int)
    }

  def filter_and_sort(self, query, sort=True):
    Model = self._get_model_class(query)
    # filter
    raws = self.args.getlist('filter')
    for raw in raws:
      try:
        key, op, value = raw.split(self.sep, 3)
      except ValueError:
        raise APIError(400, 'Invalid filter: %s' % raw)
      column = getattr(Model, key, None)
      if not column:
        raise APIError(400, 'Invalid filter column: %s' % key)
      if op == 'in':
        filt = column.in_(value.split(','))
      else:
        try:
          attr = filter(
            lambda e: hasattr(column, e % op),
            ['%s', '%s_', '__%s__']
          )[0] % op
        except IndexError:
          raise APIError(400, 'Invalid filter operator: %s' % op)
        if value == 'null':
          value = None
        filt = getattr(column, attr)(value)
      query = query.filter(filt)
    # sort
    if sort:
      raws = self.args.getlist('sort')
      for raw in raws:
        try:
          key, order = raw.split(self.sep)
        except ValueError:
          raise APIError(400, 'Invalid sort: %s' % raw)
        if not order in ['asc', 'desc']:
          raise APIError(400, 'Invalid sort order: %s' % order)
        column = getattr(Model, key, None)
        if column:
          query = query.order_by(getattr(column, order)())
        else:
          raise APIError(400, 'Invalid sort column: %s' % key)
    return query

  def offset_and_limit(self, query):
    # offset
    offset = self.args.get('offset', 0, int)
    if offset:
      query = query.offset(offset)
    # limit
    max_limit = self.defaults['MAX_LIMIT']
    limit = self.args.get('limit', self.defaults['DEFAULT_LIMIT'], int)
    if max_limit:
      limit = min(limit, max_limit) if limit else max_limit
    if limit:
      query = query.limit(limit)
    return query

  def _get_model_class(self, query):
  
    models = get_model_classes_from_query(query)

    # only tested for _BaseQueries and associated count queries
    assert len(models) < 2, 'Invalid query'

    if not len(models):
      # this is a count query
      return query._select_from_entity
    # this is a _BaseQuery
    return models[0]



