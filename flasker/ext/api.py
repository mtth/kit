#!/usr/bin/env python

"""API Extension (requires the ORM extension).

This extension provides a base class to create API views.

Setup is as follows:

.. code:: python

  from flasker import current_project as pj
  from flasker.ext import API

  api = API(pj)

  View = api.View   # the base API view

Views can then be created for models as follows:

.. code:: python

  # Cat is a subclass of flasker.ext.orm.Base

  class CatView(View):

    __model__ = Cat

This view will create the following hooks:

* ``/cats``
* ``/cats/<id>``

Another slighly more complex example:

.. code:: python

  # House is a subclass of flasker.ext.orm.Base

  class HouseView(View):

    __model__ = House

    methods = ['GET', 'POST']
    relationship_views = ['cats']

This view will create the following hooks:

* ``/houses``
* ``/houses/<id>``
* ``/houses/<id>/cats``
* ``/houses/<id>/cats/<position>``

These are only two simple ways to add a view. Please refer to the documentation
for :class:`flasker.ext.api.BaseView` for the list of all available options.

"""

from flask import Blueprint, jsonify, request
from flask.views import MethodView, View
from os.path import abspath, dirname, join
from sqlalchemy.orm import class_mapper, mapperlib
from time import time
from werkzeug.exceptions import HTTPException

from .orm import Query
from ..util import uncamelcase, query_to_models


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

  """The main API object.

  :param project: the project against which the extension will be registered
  :type project: flasker.project.Project
  :param url_prefix: the blueprint URL prefix
  :type url_prefix: str
  :param index_view: whether or not to create a splash page for the api
  :type index_view: bool
  :param parser_options: dictionary of options to create the default request
    :class:`flasker.ext.api.Parser`
  :type parser_options: dict

  """

  def __init__(self, project, url_prefix='api', index_view=True,
               parser_options=None):

    parser_options = parser_options or {}

    self.View = type(
      'View',
      (BaseView, ),
      {
        '__all__': [],
        'parser': Parser(**parser_options)
      }
    )

    @project.before_startup
    def handler(project):

      blueprint = Blueprint(
        url_prefix,
        '%s.%s' % (project.config['PROJECT']['FLASK_ROOT_FOLDER'], url_prefix),
        url_prefix='/%s' % url_prefix,
      )

      for view in self.View.__all__:
        view._attach(blueprint)

      if index_view:

        @blueprint.route('/')
        def index():
          return jsonify({
            'available_endpoints': [] #TODO
          })

      project.flask.register_blueprint(blueprint)


# Views

class _BaseViewMeta(type):

  """To register classes with the API on definition."""

  def __new__(cls, name, bases, dct):
    rv = super(_BaseViewMeta, cls).__new__(cls, name, bases, dct)
    if rv.__model__ is not None:
      rv.__all__.append(rv)
    return rv


class BaseView(View):

  """Base API view.

  To customize, override the ``get``, ``post``, etc. methods.

  """

  __metaclass__ = _BaseViewMeta
  __all__ = None

  #: orm.Model class
  __model__ = None

  #: Base URL (will default to the model's tablename).
  base_url = None

  #: Endpoint (will default to the model's tablename).
  endpoint = None

  #: Allowed methods.
  methods = frozenset(['GET'])

  #: Parser (will default to the API instance parser).
  parser = None

  #: Which relationship endpoints to create (these allow GET requests).
  #: Can be ``True`` (all relationships) or a list of relationship names.
  #: Only relationships with ``lazy`` set to ``'dynamic'``, ``'select'`` or
  #: ``True`` can have subroutes. All eagerly loaded relationships are simply
  #: available directly on the model.
  relationship_views = []

  @classmethod
  def _attach(cls, blueprint):
    """Create the URL routes for the view."""

    model = cls.__model__
    base_url = cls.base_url or model.__tablename__
    endpoint = cls.endpoint or model.__tablename__
    view = cls.as_view(endpoint)

    if 'GET' in cls.methods:
      blueprint.add_url_rule(
        rule='/%s' % (base_url, ),
        view_func=view,
        methods=['GET', ],
      )

    if 'POST' in cls.methods:
      blueprint.add_url_rule(
        rule='/%s' % (base_url, ),
        view_func=view,
        methods=['POST', ],
      )

    methods = set(['GET', 'PUT', 'DELETE']) & cls.methods
    if methods:
      blueprint.add_url_rule(
        rule='/%s%s' % (
          base_url,
          ''.join('/<%s>' % k.name for k in class_mapper(model).primary_key)
        ),
        view_func=view,
        methods=methods,
      )

    if cls.relationship_views == True:
      rels = model._get_relationships()
    else:
      rels = filter(
        lambda r: r.key in cls.relationship_views,
        model._get_relationships()
      )
    for rel in rels:
      if rel.lazy in ['dynamic', True, 'select'] and rel.uselist:
        type(
          'View',
          (_RelationshipView, ),
          {
            '__relationship__': rel,
            'parser': cls.parser,
            'base_url': base_url,
            'endpoint': '%s_%s' % (endpoint, rel.key),
          }
        )._attach(blueprint)

  def dispatch_request(self, **kwargs):
    """Dispatches requests to the corresponding method name.
    
    Similar to the ``flask.views.MethodView`` implementation: GET requests
    are passed to :meth:`get`, POST to :meth:`post`, etc.
    
    """
    meth = getattr(self, request.method.lower(), None)
    if meth is None and request.method == 'HEAD':
        meth = getattr(self, 'get', None)
    return meth(**kwargs)

  def get(self, **kwargs):
    query = self.__model__.q
    model_id = kwargs.values() if kwargs else None
    # TODO: check here if the order makes sense for composite keys
    return jsonify(self.parser.parse(query, model_id=model_id))

  def post(self):
    # TODO: validate JSON
    model = self.__model__(**request.json)
    model._flush()
    return jsonify(self.parser.serialize([model]))

  def put(self, **kwargs):
    # TODO: validate JSON
    model = self.parser._get_model(self.__model__.q, **kwargs)
    for k, v in request.json.items():
      setattr(model, k, v)
    return jsonify(self.parser.serialize([model]))

  def delete(self, **kwargs):
    model = self.parser._get_model(self.__model__.q, **kwargs)
    pj.session.delete(model)
    return jsonify({'meta': 'Resource deleted'})


class _RelationshipView(MethodView):

  """Relationship View."""

  __relationship__ = None

  base_url = None
  endpoint = None
  parser = None

  @classmethod
  def _attach(cls, blueprint):

    relationship = cls.__relationship__
    parent_model = cls.__relationship__.parent.class_

    base_url = cls.base_url
    endpoint = cls.endpoint

    view = cls.as_view(endpoint)

    blueprint.add_url_rule(
      rule='/%s%s/%s' % (
        base_url,
        ''.join(
          '/<%s>' % k.name for k in class_mapper(parent_model).primary_key
        ),
        relationship.key,
      ),
      view_func=view,
      methods=['GET', ],
    )

    blueprint.add_url_rule(
      rule='/%s%s/%s/<position>' % (
        base_url,
        ''.join(
          '/<%s>' % k.name for k in class_mapper(parent_model).primary_key
        ),
        relationship.key,
      ),
      view_func=view,
      methods=cls.methods,
    )

  def get(self, **kwargs):
    position = kwargs.pop('position', None)
    parent_model = self.__relationship__.parent.class_
    parent_instance = self.parser._get_model(parent_model.q, **kwargs)
    collection =  getattr(parent_instance, self.__relationship__.key)
    return jsonify(self.parser.parse(collection, model_position=position))


class Parser(object):

  """The request parameter parser.

  :param default_depth: the default depth models are jsonified to. ``0`` yields 
    an empty dictionary
  :type default_depth: int
  :param default_limit: the default number of results returned per query 
  :type default_limit: int
  :param max_limit: the maximum number of results returned by a query. ``0`` 
    means no limit.
  :type max_limit: int
  :param expand: if ``True``, same model data will be repeated in the response
    if the model is encountered multiple times, otherwise only the key will
    be returned. This can be very useful for efficiency when used with a 
    client-side library such as Backbone-Relational.
  :type expand: bool
  :param sep: the separator used for filters and sort parameters
  :type sep: str
  
  """

  def __init__(self, default_depth=1, default_limit=20, max_limit=0,
               expand=True, sep=';'):
    self.options = {
      'default_depth': default_depth,
      'default_limit': default_limit,
      'max_limit': max_limit,
      'expand': expand,
      'sep': sep,
    }

  def parse(self, collection, model_id=None, model_position=None):
    """Parses and serializes a list of models or a query into a dictionary.

    :param collection: the query or list to be transformed to JSON
    :type collection: flasker.ext.orm.Query, list
    :param model_id: model identifier. If specified, the parser will call
      ``get`` on the query with this id.
    :type model_id: varies
    :param model_position: position of the model in the collection
    :type model_position: int
    :rtype: dict

    This method is convenience for calling :meth:`process` followed by
    :meth:`serialize`, with the content key parameter smartly chosen to 
    abide by ``flask.jsonify``'s limitation to only objects as top level.

    Also adds a match count and request overview for wrapped responses.

    """
    collection, match = self.process(
      collection,
      model_id=model_id,
      model_position=model_position
    )
    if isinstance(collection, Query) or len(collection) > 1:
      content_key = 'data'
    else:
      content_key = None
    return self.serialize(
      collection,
      content_key=content_key,
      meta={
        'request': {
          'base_url': request.base_url,
          'method': request.method,
          'values': request.values,
        },
        'match': match
      }
    )

  def process(self, collection, model_id=None, model_position=None):
    """Parse query and return JSON.

    :param collection: the query or list to be transformed to JSON
    :type collection: flasker.ext.orm.Query, list
    :param model_id: model identifier. If specified, the parser will call
      ``get`` on the query with this id.
    :type model_id: varies
    :param model_position: position of the model in the collection (1 indexed).
    :type model_position: int
    :rtype: tuple

    Returns a tuple ``(collection, match)``:

    * ``collection`` is the filtered, sorted, offsetted, limited collection
    * ``match`` is a dictionary with two keys: ``total`` with the total number
      of results from the filtered query and ``returned`` with the total number
      of results for the filtered, offsetted and limited query.

    """

    if not collection:
      return []

    if model_id or model_position:

      if model_id:
        collection = [collection.get(model_id)]
      else:
        position = int(model_position) - 1 # model_position is 1 indexed
        if isinstance(collection, list):
          collection = collection[position:(position + 1)]
        else:
          collection = collection.offset(position).limit(1).all()

      match = {'total': len(collection), 'returned': len(collection)}

    else:
      model = self._get_model_class(collection)

      raw_filters = request.args.getlist('filter')
      raw_sorts = request.args.getlist('sort')

      offset = request.args.get('offset', 0, int)
      limit = request.args.get('limit', self.options['default_limit'], int)
      max_limit = self.options['max_limit']
      if max_limit:
        limit = min(limit, max_limit) if limit else max_limit

      if isinstance(collection, list):

        if raw_filters or raw_sorts:
          raise APIError(400, 'Filter and sorts not implemented for lists')

        match = {'total': len(collection)}

        if limit:
          collection = collection[offset:(offset + limit)]
        else:
          collection = collection[offset:]

        match['returned'] = len(collection)

      else:

        sep = self.options['sep']

        for raw_filter in raw_filters:
          try:
            key, op, value = raw_filter.split(sep, 3)
          except ValueError:
            raise APIError(400, 'Invalid filter: %s' % raw_filter)
          column = getattr(model, key, None)
          if not column: # TODO check if is actual column
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
          collection = collection.filter(filt)

        for raw_sort in raw_sorts:
          try:
            key, order = raw_sort.split(sep)
          except ValueError:
            raise APIError(400, 'Invalid sort: %s' % raw_sort)
          if not order in ['asc', 'desc']:
            raise APIError(400, 'Invalid sort order: %s' % order)
          column = getattr(model, key, None)
          if column:
            collection = collection.order_by(getattr(column, order)())
          else:
            raise APIError(400, 'Invalid sort column: %s' % key)

        match = {'total': collection.count()}

        if offset:
          collection = collection.offset(offset)

        if limit:
          collection = collection.limit(limit)

        match['returned'] = collection.count()

    return collection, match

  def serialize(self, collection, content_key=None, **kwargs):
    """Serializes a list or query to a dictionary.

    :param collection: the collection to be serialized
    :type collection: iterable
    :param content_key: key to wrap content in
    :type content_key: str
    :rtype: dict
    
    The keyword arguments are ignored if ``content_key`` is ``None`` and
    used to update the returned dictionary otherwise.

    """

    depth = request.args.get('depth', self.options['default_depth'], int)
    expand = request.args.get('expand', self.options['expand'], int)

    content = [
      e.to_json(depth=depth, expand=expand)
      for e in collection
      if e
    ]

    if not content:
      raise APIError(404, 'Resource not found')

    if not content_key:
      if len(content) == 1:
        return content[0]
      else:
        return content
    else:
      rv = kwargs or {}
      rv[content_key] = content
      return rv

  def _get_model_class(self, collection):
    """Return corresponding model class from collection."""
  
    if isinstance(collection, Query):
      models = query_to_models(collection)

      # only tested for _BaseQueries and associated count queries
      assert len(models) < 2, 'Invalid query'

      if not len(models):
        # this is a count query
        return collection._select_from_entity
      else:
        # this is a Query
        return models[0]

    else:
      return collection[0].__class__

  def _get_model(self, query, **kwargs):
    """Get model instance from a query and keyword arguments."""
    model_id = kwargs.values() if kwargs else None
    collection, match = self.process(query, model_id)
    assert len(collection) <= 1, 'Multiple models found'
    if len(collection):
      return collection[0]
    else:
      raise APIError(404, 'Resource not found')

