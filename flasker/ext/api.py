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
from os.path import abspath, dirname, join
from sqlalchemy.orm import class_mapper
from time import time
from werkzeug.exceptions import HTTPException

from ..util.flask import make_view, View as _View, _ViewMeta
from ..util.helpers import uncamelcase
from ..util.sqlalchemy import Model, Query, query_to_models


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
      '%s.%s' % (project.flask.name, url_prefix),
      url_prefix='/%s' % url_prefix,
    )

    self.View = make_view(
      blueprint,
      view_class=View,
      parser=Parser(**parser_options)
    )

    @project.run_after_module_imports
    def api_after_imports(project):

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
      project.logger.debug('api blueprint registered')

    project.logger.debug('api extension initialized')


class _ApiViewMeta(_ViewMeta):

  """To register classes with the API on definition.

  Automatically creates the ``endpoint``, ``base_url`` and ``rules`` for the
  view from the ``__model__`` attribute.

  Each route is then registered on the bound application (the current API
  blueprint here).
  
  """

  def __new__(cls, name, bases, dct):

    model = dct.get('__model__', None)

    if model is not None:
      if not issubclass(model, Model):
        raise ValueError('Api views can only be used with Orm models.')

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
  def register_view(cls, blueprint):
    """Create the URL routes for the view.
    
    Standard :class:`flasker.util.View` implementation plus subview support.
    
    """

    super(View, cls).register_view(blueprint)

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
          __model__=model,
          __assoc_key__=key,
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
    if kwargs:
      model = self.__model__.retrieve(from_key=True, **kwargs)
      if not model:
        raise APIError(404, 'Not found')
      return self.parser.jsonify(model)
    else:
      return self.parser.jsonify(self.__model__.q)

  def post(self):
    """POST request handler."""
    if not self.validate(json):
      raise APIError(400, 'Invalid POST parameters')
    model = self.__model__(**request.json)
    model.flush()
    return self.parser.jsonify(model)

  def put(self, **kwargs):
    """PUT request handler."""
    model = self.__model__.retrieve(from_key=True, **kwargs)
    if not model:
      raise APIError(404, 'Not found')
    if not self.validate(json, model):
      raise APIError(400, 'Invalid PUT parameters')
    for k, v in request.json.items():
      setattr(model, k, v)
    return self.parser.jsonify(model)

  def delete(self, **kwargs):
    """DELETE request handler."""
    model = self.__model__.retrieve(from_key=True, **kwargs)
    if not model:
      raise APIError(404, 'Not found')
    pj.session.delete(model)
    return self.parser.jsonify(model)

  def validate(self, json, model=None):
    """Validation method.

    :param json: a dictionary of attributes
    :type json: dict
    :param model: ``None`` if it is POST request, and the model instance to be
      modified if it is a PUT request.
    :type model: None or flasker.ext.orm.BaseModel
    :rtype: bool

    This method is called on each POST and PUT request. Override it to
    implement your own validation logic: return ``True`` when the input is
    valid and ``False`` otherwise. Default implementation accepts everything.

    """
    return True
  

class _RelationshipView(_View):

  """Relationship View."""

  __model__ = None
  __assoc_key__ = None

  def get(self, **kwargs):
    """GET request handler."""
    position = kwargs.pop('position', None)
    parent = self.__model__.retrieve(from_key=True, **kwargs)
    if not parent:
      raise APIError(404, 'Parent not found')
    collection =  getattr(parent, self.__assoc_key__)

    if position:
      position = int(position) - 1 # model_position is 1 indexed
      if isinstance(collection, Query):
        model = collection.offset(position).limit(1).first()
      else:
        collection = collection[position:(position + 1)]
        model = collection[0] if collection else None
        if not model:
          raise APIError(404, 'Not found')
      return self.parser.jsonify(model)

    else:
      return self.parser.jsonify(collection)


class Parser(object):

  """The request parameter parser.

  :param default_depth: the default depth models are jsonified to. ``0`` yields 
    an empty dictionary
  :type default_depth: int
  :param max_depth: the maximum depth allowed in a query. ``0`` means no limit.
  :type max_depth: int
  :param default_limit: the default number of results returned per query 
  :type default_limit: int
  :param max_limit: the maximum number of results returned by a query. ``0`` 
    means no limit.
  :type max_limit: int
  :param sep: the separator used for filters and sort parameters
  :type sep: str

  This class has a single method :meth:``jsonify`` which is used to parse a
  model or collection and return the serialized response.
  
  """

  def __init__(self, default_depth=1, max_depth=0, default_limit=20,
               max_limit=0, sep=';'):
    self.options = {
      'default_depth': default_depth,
      'max_depth': max_depth,
      'default_limit': default_limit,
      'max_limit': max_limit,
      'sep': sep,
    }

  def jsonify(self, data, data_key='data', meta_key='meta',
    include_request=True, include_time=True, include_matches=True, **kwargs):
    """Parses the data and returns the serialized response.

    :param data: data. At this time, only instances, and lists of instances of
      ``flasker.util.sqlalchemy.Model``, along with instances of 
      ``flasker.util.sqlalchemy.Query`` are valid.
    :type data: model or collection
    :param data_key: key where the serialized data will go
    :type data_key: str
    :param meta_key: key where the metadata will go
    :type meta_key: str
    :param include_request: whether or not to include the issued request
      information
    :type include_request: bool
    :param include_time: whether or not to include processing time
    :type include_time: bool
    :param include_matches: whether or not to include the total number of
      results from the data (useful if ``data`` is a collection)
    :type include_matches: bool
    :rtype: Flask response
    
    Any keyword arguments will be included with the metadata.
    
    """
    depth = request.args.get('depth', self.options['default_depth'], int)
    max_depth = self.options['max_depth']
    if max_depth:
      depth = min(depth, max_depth)

    start = time()

    if isinstance(data, Model):
      data = data.to_json(depth=depth)
      match = 1
    else:
      col, matches = self._get_collection(data)
      data = [e.to_json(depth=depth) for e in col if e]
      match = {'total': matches, 'returned': len(data)}

    rv = {data_key: data, meta_key: kwargs}

    if include_matches:
      rv[meta_key]['matches'] = match
    if include_request:
      rv[meta_key]['request'] = {
        'base_url': request.base_url,
        'method': request.method,
        'values': request.values,
      }
    if include_time:
      rv[meta_key]['parsing_time'] = time() - start

    return jsonify(rv)

  def _get_collection(self, collection):
    """Parse query and return JSON.

    :param collection: the query or list to be transformed to JSON
    :type collection: flasker.ext.orm.Query, list
    :rtype: tuple

    Returns a tuple ``(collection, match)``:

    * ``collection`` is the filtered, sorted, offsetted, limited collection.
    * ``match`` is the total number of results from the filtered query 

    """
    model = self._get_model_class(collection)
    raw_filters = request.args.getlist('filter')
    raw_sorts = request.args.getlist('sort')
    offset = request.args.get('offset', 0, int)
    limit = request.args.get('limit', self.options['default_limit'], int)
    max_limit = self.options['max_limit']
    if max_limit:
      limit = min(limit, max_limit) if limit else max_limit

    if isinstance(collection, Query):

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

      matches = collection.fast_count()
      if offset:
        collection = collection.offset(offset)
      if limit:
        collection = collection.limit(limit)

    else:
      if raw_filters or raw_sorts:
        raise APIError(400, 'Filter and sorts not implemented for lists')

      matches = len(collection)
      if limit:
        collection = collection[offset:(offset + limit)]
      else:
        collection = collection[offset:]

    return collection, matches

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

