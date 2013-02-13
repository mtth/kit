#!/usr/bin/env python

"""API Extension."""

from flask import Blueprint, jsonify, request
from flask.views import View
from os.path import abspath, dirname, join
from sqlalchemy import Column, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import class_mapper, mapperlib, Query
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.dynamic import AppenderQuery
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty
from time import time
from werkzeug.exceptions import HTTPException

from ..project import current_project as pj
from ..util import (Cacheable, _jsonify, JSONDepthExceededError,
  JSONEncodedDict, Loggable, uncamelcase)

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
    'RELATIONSHIPS': True,
    'DEFAULT_DEPTH': 0,
    'DEFAULT_LIMIT': 20,
    'MAX_LIMIT': None,
  }

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      self.config[k.upper()] = v
    APIView.__extension__ = self
    self.Models = {}

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
    CollectionView.attach_view(Model)
    ModelView.attach_view(Model)
    for rel in Model.get_relationships():
      if rel.lazy == 'dynamic' and rel.uselist:
        RelationshipModelView.attach_view(rel)
        DynamicRelationshipView.attach_view(rel)
      elif rel.lazy == True and rel.uselist:
        RelationshipModelView.attach_view(rel)
        LazyRelationshipView.attach_view(rel)

  def _before_register(self, project):
    self.blueprint = Blueprint(
      'api',
      project.config['PROJECT']['APP_FOLDER'] + '.api',
      template_folder=abspath(join(dirname(__file__), 'templates', 'api')),
      url_prefix=self.config['URL_PREFIX']
    )
    if self.config['ADD_ALL_MODELS']:
      for model_class in [k.class_ for k in mapperlib._mapper_registry]:
        if not model_class.__name__ in self.Models:
          self.add_model(model_class)
    for model_class, options in self.Models.values():
      self._create_model_views(model_class, options)
    IndexView.attach_view()

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

  def fast_count(self):
    """Counting without subqueries."""
    Model = self.base_model_class
    primary_keys = [
      getattr(Model, key)
      for key in Model.get_primary_key_names()
    ]
    return pj.session.query(func.count(*primary_keys)).one()[0]

  def get_count_query(self):
    Model = self.base_model_class
    query = pj.session.query(func.count(Model)).select_from(Model)
    query.base_model_class = Model
    return query

class _QueryProperty(object):

  def __init__(self, project):
    self.project = project

  def __get__(self, obj, cls):
    try:
      mapper = class_mapper(cls)
      if mapper:
        query =  _BaseQuery(mapper, session=self.project.session())
        query.base_model_class = cls
        return query
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
  def __tablename__(cls):
    """Automatically create the table name.

    Override this to choose your own tablename (e.g. for single table
    inheritance).

    """
    return '%ss' % uncamelcase(cls.__name__)

  @declared_attr
  def __json__(cls):
    return dict(
      (varname, 1)
      for varname in dir(cls)
      if not varname.startswith('_')  # don't show private properties
      if (
        isinstance(getattr(cls, varname), property) 
      ) or (
        isinstance(getattr(cls, varname), InstrumentedAttribute) and
        isinstance(getattr(cls, varname).property, ColumnProperty) and
        not getattr(cls, varname).foreign_keys
      ) or (
        isinstance(getattr(cls, varname), InstrumentedAttribute) and
        isinstance(getattr(cls, varname).property, RelationshipProperty)
        and getattr(cls, varname).property.lazy in [False, 'joined']
      )
    )

  def jsonify(self, depth=1):
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
    for varname, cost in self.__json__.iteritems():
      try:
        rv[varname] = _jsonify(getattr(self, varname), depth - cost)
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
  def get_relationships(cls, show_private=False):
    rels =  class_mapper(cls).relationships.values()
    if not show_private:
      rels = [rel for rel in rels if not rel.key.startswith('_')]
    return rels

  @classmethod
  def get_related_models(cls):
    return [(r.key, r.mapper.class_) for r in cls.get_relationships()]

  @classmethod
  def get_primary_key_names(cls):
    return [key.name for key in class_mapper(cls).primary_key]


Model = declarative_base(cls=ExpandedBase)

# Error

class APIError(HTTPException):

  """Thrown when an API call is invalid."""

  def __init__(self, code, content):
    self.code = code
    self.content = content
    super(APIError, self).__init__(content)

  def __repr__(self):
    return '<APIError %r: %r>' % (self.message, self.content)

# Views

class APIView(View):

  """Base API view.

  Note that the methods class attribute seems to be passed to the add_url_rule
  function somehow (!).

  A collection can either be:

  * a query (most cases)
  * an instrumented list (in the case of relationships)

  """

  __all__ = []
  __extension__ = None

  # Flask stuff
  decorators = []
  methods = frozenset(['get', 'post', 'head', 'options',
                       'delete', 'put', 'trace', 'patch'])

  allowed_request_keys = frozenset()

  def __call__(self, *args, **kwargs):
    method = getattr(self, request.method.lower(), None)
    if method is None and request.method == 'HEAD':
      method = getattr(self, 'get', None)
    try:
      if not method:
        raise APIError(405, 'Method Not Allowed')
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
    return uncamelcase(self.__class__.__name__)

  def get_rule(self):
    return self.url

  @classmethod
  def attach_view(cls, *view_args, **view_kwargs):
    view = cls(*view_args, **view_kwargs)
    cls.__extension__.blueprint.add_url_rule(
      rule=view.get_rule(),
      endpoint=view.get_endpoint(),
      view_func=view,
      methods=cls.methods
    )
    cls.__all__.append(view)

  @classmethod
  def get_available_methods(cls):
    return set(dir(cls)) & cls.methods

class CollectionView(APIView):

  """View for collection endpoints."""

  allowed_request_keys = frozenset(['depth', 'limit', 'offset', 'filter', 
                                    'sort'])

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
      e.jsonify(parser.get_depth())
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
    if self.is_validated(request.json):
      if not self.rel:
        model = self.Model(**request.json)
      else:
        parent = self.Model.query.get(kwargs.values())
        if not parent:
          raise APIError(404, 'No resource found for this ID')
        Model = self.rel.mapper.class_
        model = Model(**request.json)
        # TODO automatically add parent_id to backref
      pj.session.add(model)
      pj.session.commit() # generate an ID
      return jsonify(model.jsonify(depth=allowed_request_keys['depth']))
    else:
      raise APIError(400, 'Failed validation')

class ModelView(APIView):

  """View for individual model endpoints."""

  allowed_request_keys = frozenset(['depth'])

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
    return jsonify(model.jsonify(depth=parser.get_depth()))

  def put(self, parser, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if model:
      if self.is_validated(request.json):
        for k, v in request.json.items():
          setattr(model, k, v)
        return jsonify(model.jsonify(depth=allowed_request_keys['depth']))
      else:
        raise APIError(400, 'Failed validation')
    else:
      raise APIError(404, 'No resource found for this ID')

  def delete(self, parser, **kwargs):
    model = self.Model.query.get(kwargs.values())
    if model:
      pj.session.delete(model)
      return jsonify({'status': '200 Success', 'content': 'Resource deleted'})
    else:
      raise APIError(404, 'No resource found for this ID')

class RelationshipView(APIView):

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
      self.parent_Model.__name__,
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

  allowed_request_keys = frozenset(['depth', 'limit', 'offset', 'filter',
                                    'sort'])

  def get(self, parser, **kwargs):
    query = parser.filter_and_sort(self.get_collection(**kwargs))
    timers = {}
    now = time()
    count = query.count()
    timers['count'] = time() - now
    now = time()
    content = [
      e.jsonify(parser.get_depth())
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

  allowed_request_keys = frozenset(['depth'])

  def get(self, parser, **kwargs):
    timers = {}
    now = time()
    content = [
      e.jsonify(parser.get_depth())
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

  def post(self, **kwargs):
    pass

class RelationshipModelView(RelationshipView):

  allowed_request_keys = frozenset(['depth'])

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
    return jsonify(model.jsonify(depth=parser.get_depth()))

  def put(self, parser, **kwargs):
    pass

class IndexView(APIView):

  """API 'splash' page with a few helpful keys."""

  url = '/'

  def get(self, params, **kwargs):
    return jsonify({
      'status': '200 Welcome',
      'available_endpoints': [
        '%s (%s)' % (
          view.get_rule(),
          ', '.join(m.upper() for m in view.get_available_methods()))
        for view in self.__all__
      ]
    })

# Helper

class Parser(object):

  sep = ';'

  def __init__(self, allowed_keys):
    self.args = request.args
    self.keys = set(self.args.keys())
    if not self.keys <= set(allowed_keys):
      raise APIError(400, 'Invalid parameters found: %s not in %s' % (
        list(self.keys), list(allowed_keys)
       ))

  def get_depth(self):
    return self.args.get('depth', 1, int)

  def filter_and_sort(self, query, sort=True):
    Model = self._get_Model(query)
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
    limit = self.args.get('limit', 20, int)
    if limit:
      query = query.limit(limit)
    return query

  def _get_Model(self, query):
    if hasattr(query, 'base_model_class'):
      # this is a global query
      return query.base_model_class
    else:
      # this is a relationship appenderquery
      return query.attr.target_mapper.class_
