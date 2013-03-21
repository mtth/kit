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
from flask.views import View
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

    self._views = []

    self.parser = Parser(parser_options or {})

    self.View = type(
      'View',
      (BaseView, ),
      {
        '__all__': self._views,
        'url_prefix': url_prefix,
      }
    )

    @project.before_startup
    def handler(project):
      blueprint = Blueprint(
        url_prefix,
        '%s.%s' % (project.config['PROJECT']['FLASK_ROOT_FOLDER'], url_prefix),
        # template_folder=abspath(join(dirname(__file__), 'templates', 'api')),
        url_prefix='/%s' % url_prefix,
      )
      for view in self._views:
        view._attach_views(blueprint)
      if index_view:
        IndexView._attach(blueprint)
      project.flask.register_blueprint(blueprint)


# Views

class _BaseViewMeta(type):

  """To register classes with the API on definition."""

  def __new__(cls, name, bases, dct):
    rv = super(_BaseViewMeta, cls).__new__(cls, name, bases, dct)
    if rv.__all__ is not None:
      rv.__all__.append(rv)
    return rv


class BaseView(View):

  """Base API view. Not an actual view.

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

  __metaclass__ = _BaseViewMeta

  __all__ = None

  #: orm.Model class
  __model__ = None

  #: Allowed methods.
  methods = frozenset(['GET'])

  #: Whether or not to create the collection endpoint.
  collection_view = True

  #: Whether or not to create the model endpoint.
  model_view = True

  #: Which relationship endpoints to create.
  #: can be ``True`` (all relationships), a list of relationship attributes
  #: names or a dictionary with keys being relationship attributes and values
  #: tuples of (RelationshipCollectionView, RelationshipModelView).
  relationship_views = []

  @classmethod
  def _attach_views(cls, blueprint):
    Model = cls.__model__
    if cls.collection_view:
      CollectionView._attach(Model, cls.methods)
    if cls.model_view:
      ModelView._attach(Model, cls.methods)
    if relationships == True:
      rels = Model._get_relationships()
    elif relationships == False:
      rels = []
    else:
      rels = filter(
        lambda r: r.key in relationships,
        Model._get_relationships()
      )
    for rel in rels:
      if rel.lazy == 'dynamic' and rel.uselist:
        RelationshipModelView._attach(rel, **options)
        DynamicRelationshipView.attach_view(rel, **options)
      elif rel.lazy in [True, 'select'] and rel.uselist:
        RelationshipModelView.attach_view(rel, **options)
        LazyRelationshipView.attach_view(rel, **options)

  @classmethod
  def _get_endpoint(cls):
    """Returns the endpoint for use in the blueprint.

    These should be unique accross all your API views.
    
    """
    return uncamelcase(clf.__model__.__name__)

  def get_rule(self):
    """Returns the URL route for the view.

    Routes should be unique (duh).

    """
    return self.url

  def get(self, **kwargs):
    timers = {}
    filtered_query = parser.filter_and_sort(self.Model.q )
    now = time()
    count = parser.filter_and_sort(self.Model.c, False).scalar()
    timers['count'] = time() - now
    now = time()
    content = [
      e.to_json(**parser.get_jsonify_kwargs())
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

  def post(self):
    if self._is_valid(self.Model, request.json):
      model = self.Model(**request.json)
      pj.session.add(model)
      pj.session.commit() # generate an ID
      return jsonify(model.to_json(**parser.get_jsonify_kwargs()))
    else:
      raise APIError(400, 'Failed validation')

  def put(self, **kwargs):
    model = self.Model.q.get(kwargs.values())
    if model:
      if self._is_valid(model.__class__, request.json):
        for k, v in request.json.items():
          setattr(model, k, v)
        return jsonify(model.to_json(**parser.get_jsonify_kwargs()))
      else:
        raise APIError(400, 'Failed validation')
    else:
      raise APIError(404, 'No resource found for this ID')

  def delete(self, **kwargs):
    model = self.Model.q.get(kwargs.values())
    if model:
      pj.session.delete(model)
      return jsonify({'status': '200 Success', 'content': 'Resource deleted'})
    else:
      raise APIError(404, 'No resource found for this ID')

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

  def get_endpoint(self):
    return 'collection_view_for_%s' % self.Model.__tablename__
    return 'model_view_for_%s' % self.Model.__tablename__

  def get_rule(self):
    url = '/%s' % self.Model.__tablename__
    url += ''.join('/<%s>' % k.name for k in class_mapper(self.Model).primary_key)
    return url
    return '/%s' % self.Model.__tablename__


class RelationshipView(View):

  """Not an actual view, meant to be subclassed."""

  __model__ = None
  __relationship__ = None

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
      '/<%s>' % k.name for k in class_mapper(self.parent_Model).primary_key
    )
    url += '/%s' % self.rel.key
    return url

  def get_collection(self, **kwargs):
    parent_model = self.parent_Model.q.get(kwargs.values())
    if not parent_model:
      raise APIError(404, 'No resource found')
    return getattr(parent_model, self.rel.key)

  def get(self, **kwargs):
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
    return jsonify(model.to_json(**parser.get_jsonify_kwargs()))

  def get(self, **kwargs):
    return jsonify({
      'status': '200 Success',
    }), 200

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
      '/<%s>' % k.name for k in class_mapper(self.parent_Model).primary_key
    )
    url += '/%s/<key>' % self.rel.key
    return url


class IndexView(View):

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


# Helper

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
    :meth:`flasker.ext.api.Parser.serialize`, with the following variant.
    When using this method, the ``wrap`` parameter is determined by the type
    of ``collection``:

    * ``wrap=True`` if ``collection`` is a :class:`flasker.ext.orm.Query` and
      ``model_id`` and ``model_position`` are ``None``
    * ``wrap=False`` otherwise

    """
    collection, match = self.process(
      collection,
      model_id=model_id,
      model_position=model_position
    )
    content_key = 'data' if isinstance(collection, Query) else None
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
    :param model_position: position of the model in the collection
    :type model_position: int
    :rtype: tuple

    Returns a tuple ``(collection, info)``.

    """
    # keys = set(request.args.keys())
    # if not keys <= set(allowed_keys):
    #   raise APIError(400, 'Invalid parameters found: %s not in %s' % (
    #     list(self.keys), list(allowed_keys)
    #   ))

    processing_timer = time()

    if model_id or model_position:

      if model_id:
        collection = [collection.get(model_id)]
      else:
        position = model_position - 1 # model_position is 1 indexed
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
    :param content_key: key to wrap content in
    :param kwargs: ignored if ``content_key`` is ``None``

    """

    depth = request.args.get('depth', self.options['default_depth'], int)
    expand = request.args.get('expand', self.options['expand'], int)

    content = [
      e.to_json(depth=depth, expand=expand)
      for e in collection
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

  def _get_model_class(self, query):
    """Return corresponding model class from query."""
  
    models = query_to_models(query)

    # only tested for _BaseQueries and associated count queries
    assert len(models) < 2, 'Invalid query'

    if not len(models):
      # this is a count query
      return query._select_from_entity
    # this is a Query
    return models[0]

