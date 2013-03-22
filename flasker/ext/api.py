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
    subviews = ['cats']

This view will create the following hooks:

* ``/houses``
* ``/houses/<id>``
* ``/houses/<id>/cats``
* ``/houses/<id>/cats/<position>``

These are only two simple ways to add a view. Please refer to the documentation
for :class:`flasker.ext.api.BaseView` for the list of all available options.

"""

from flask import Blueprint, jsonify, request
from flasker.util import make_view, View as _View, _ViewMeta
from os.path import abspath, dirname, join
from sqlalchemy.ext.associationproxy import AssociationProxy
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

    blueprint = Blueprint(
      url_prefix,
      '%s.%s' % (project.config['PROJECT']['FLASK_ROOT_FOLDER'], url_prefix),
      url_prefix='/%s' % url_prefix,
    )

    self.View = make_view(
      blueprint,
      view_class=View,
      parser=Parser(**parser_options)
    )

    @project.before_startup
    def handler(project):

      if index_view:

        @blueprint.route('/')
        def index():
          return jsonify({
            'available_endpoints': sorted(
              '%s (%s)' % (r.rule, ', '.join(str(meth) for meth in r.methods))
              for r in project.flask.url_map.iter_rules()
              if r.endpoint.startswith('%s.' % url_prefix)
            )
          })

      project.flask.register_blueprint(blueprint)


class _ApiViewMeta(_ViewMeta):

  """To register classes with the API on definition."""

  def __new__(cls, name, bases, dct):

    model = dct.get('__model__', None)

    if model is not None:
      dct.setdefault('endpoint', model.__tablename__)
      base_url = dct.setdefault('base_url', model.__tablename__)

      collection_route = '/%s' % (base_url, )
      model_route = '/%s%s' % (
        base_url,
        ''.join('/<%s>' % k.name for k in class_mapper(model).primary_key)
      )

      dct['rules'] = {
        collection_route: ['GET', 'POST'],
        model_route: ['GET', 'PUT', 'DELETE'],
      }

    return super(_ApiViewMeta, cls).__new__(cls, name, bases, dct)


class View(_View):

  """Base API view.

  To customize, override the ``get``, ``post``, etc. methods.

  """

  __metaclass__ = _ApiViewMeta

  #: orm.Model class
  __model__ = None

  #: Base URL (will default to the model's tablename).
  base_url = None

  #: Allowed methods.
  methods = frozenset(['GET'])

  #: Request parser.
  parser = None

  #: Which relationship endpoints to create (these allow GET requests).
  #: Can be ``True`` (all relationships) or a list of relationship names.
  #: Only relationships with ``lazy`` set to ``'dynamic'``, ``'select'`` or
  #: ``True`` can have subroutes. All eagerly loaded relationships are simply
  #: available directly on the model.
  subviews = []

  @classmethod
  def bind_view(cls, blueprint):
    """Create the URL routes for the view.
    
    Standard :class:`flasker.util.View` implementation plus subview support.
    
    """

    super(View, cls).bind_view(blueprint)

    if cls.subviews:
      
      model = cls.__model__

      all_keys = set(
        model._get_relationships(
          lazy=['dynamic', True, 'select'],
          uselist=True
        ).keys() +
        model._get_association_proxies().keys()
      )

      if cls.subviews == True:
        keys = all_keys
      else:
        keys = set(cls.subviews)
        if keys - all_keys:
          raise ValueError('%s invalid for subviews' % (keys - all_keys, ))
        keys = all_keys & keys

      for key in keys:

        collection_route = '/%s%s/%s' % (
          cls.base_url,
          ''.join(
            '/<%s>' % k.name for k in class_mapper(model).primary_key
          ),
          key,
        )
        model_route = '/%s%s/%s/<position>' % (
          cls.base_url,
          ''.join(
            '/<%s>' % k.name for k in class_mapper(model).primary_key
          ),
          key
        )

        make_view(
          blueprint,
          view_class=_RelationshipView,
          view_name='%s_%s' % (cls.endpoint, key),
          parent_model=model,
          assoc_key=key,
          parser=cls.parser,
          endpoint='%s_%s' % (cls.endpoint, key),
          methods=['GET', ],
          rules={
            collection_route: ['GET', ],
            model_route: ['GET', ],
          },
        )

  def get(self, **kwargs):
    """GET request handler."""
    query = self.__model__.q
    model_id = filter(None, kwargs.values()) if kwargs else None
    # TODO: check here if the order makes sense for composite keys
    return jsonify(self.parser.parse(query, model_id=model_id))

  def post(self):
    """POST request handler."""
    # TODO: validate JSON
    model = self.__model__(**request.json)
    model._flush()
    return jsonify(self.parser.serialize([model]))

  def put(self, **kwargs):
    """PUT request handler."""
    # TODO: validate JSON
    model = self.parser._get_model(self.__model__.q, **kwargs)
    for k, v in request.json.items():
      setattr(model, k, v)
    return jsonify(self.parser.serialize([model]))

  def delete(self, **kwargs):
    """DELETE request handler."""
    model = self.parser._get_model(self.__model__.q, **kwargs)
    pj.session.delete(model)
    return jsonify({'meta': 'Resource deleted'})


class _RelationshipView(_View):

  """Relationship View."""

  parent_model = None
  assoc_key = None

  def get(self, **kwargs):
    """GET request handler."""
    position = kwargs.pop('position', None)
    parent_model = self.parent_model
    parent_instance = self.parser._get_model(parent_model.q, **kwargs)
    collection =  getattr(parent_instance, self.assoc_key)
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
    :meth:`serialize`, with a match count and request overview.

    """
    collection, match = self.process(
      collection,
      model_id=model_id,
      model_position=model_position
    )
    return self.serialize(
      collection,
      content_key='data',
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
      return [], None

    if model_id or model_position:

      if model_id:
        model = collection.get(model_id)
        collection = [model] if model else []
      else:
        position = int(model_position) - 1 # model_position is 1 indexed
        if isinstance(collection, Query):
          collection = collection.offset(position).limit(1).all()
        else:
          collection = collection[position:(position + 1)]

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

      if isinstance(collection, Query):

        # TODO: speedup counting

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

      else:

        if raw_filters or raw_sorts:
          raise APIError(400, 'Filter and sorts not implemented for lists')

        match = {'total': len(collection)}

        if limit:
          collection = collection[offset:(offset + limit)]
        else:
          collection = collection[offset:]

        match['returned'] = len(collection)

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

    if not content_key:
      if len(content) == 0:
        raise APIError(404, 'Resource not found')
      elif len(content) == 1:
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

