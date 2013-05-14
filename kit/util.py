#!/usr/bin/env python

"""Utility module."""

from collections import namedtuple
from datetime import datetime, timedelta
from decimal import Decimal
from flask import request
from flask.views import View as _View
from logging import getLogger
from re import sub
from json import dumps, loads
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.types import TypeDecorator, UnicodeText
from time import time

try:
  from pandas import DataFrame
except ImportError:
  pass


def uncamelcase(name):
  """Transforms CamelCase to underscore_case.

  :param name: string input
  :type name: str
  :rtype: str
  
  """
  first = sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
  return sub('([a-z0-9])([A-Z])', r'\1_\2', first).lower()

def to_json(value, depth=1):
  """Serialize an object.

  :param value: the object to be serialized.
  :type value: varies
  :param depth: used when serializing nested objects with a ``to_json``
    method. In that case, the ``depth`` parameter is decremented by one each
    call. This paramater sets the initial value.
  :type depth: int
  :rtype: varies

  """
  if hasattr(value, 'to_json'):
    return value.to_json(depth - 1)
  if isinstance(value, dict):
    return {k: to_json(v, depth) for k, v in value.items()}
  if isinstance(value, (list, tuple)):
    return [to_json(v, depth) for v in value]
  if isinstance(value, (float, int, long, str, unicode)):
    return value
  if value is None:
    return None
  if isinstance(value, (datetime, timedelta)):
    return str(value)
  if isinstance(value, Decimal):
    return float(value)
  raise ValueError('Not jsonifiable')


# Mixins
# ======

class Jsonifiable(object):

  """JSONification mixin."""

  @property
  def __json__(self):
    """Default implementation of the attributes to jsonify.

    This is relatively slow (because it is evaluated for each jsonify call).
    Consider overwriting it for better performance.
    
    """
    return [
      varname for varname in dir(self)
      if not varname.startswith('_')
      if not callable(getattr(self, varname))
    ]

  def to_json(self, depth=1):
    """Returns all keys and properties of an instance in a dictionary.

    :param depth:
    :type depth: int
    :rtype: dict

    """
    rvd = {}
    if depth < 1:
      return rvd
    for varname in self.__json__:
      try:
        rvd[varname] = to_json(getattr(self, varname), depth)
      except ValueError as err:
        rvd[varname] = err.message
    return rvd


class Loggable(object):

  """Convenient logging mixin."""

  __logger__ = None

  @property
  def logger(self):
    """The class logger."""
    if not self.__logger__:
      self.__logger__ = getLogger(self.__module__)
    return self.__logger__


CACHE_REFRESH = namedtuple('CACHE_REFRESH', ['expiration'])


class Cacheable(object):

  """Mixin to support cacheable properties.
  
  Implements a few cache maintenance utilities as well.
  
  """

  __cache__ = None

  def _get_cached_properties(self):
    """Private method to return the list of cached properties."""
    return [
        varname
        for varname in dir(self.__class__)
        if isinstance(getattr(self.__class__, varname), _CachedProperty)
    ]

  def refresh_cache(self, names=None, expiration=0, remove_deleted=True):
    """Refresh this instance's cached properties.

    :param names: list of cached property names to refresh. If specified, only
      these will be refreshed.
    :type names: iterable
    :param expiration: if specified, only properties of age greater than this
      value will be refreshed (seconds).
    :type expiration: int
    :param remove_deleted: if ``True``, cached properties that aren't defined
      but are still present in the cache will be removed (useful especially for
      persistent caches)
    :type remove_deleted: bool

    """
    cached_properties = set(self._get_cached_properties())

    if names:
      for name in names:
        if name in cached_properties:
          setattr(self, name, CACHE_REFRESH(expiration))
        else:
          raise AttributeError('No cached property %r on %r.' % (name, self))
    else:
      for varname in cached_properties:
        setattr(self, varname, CACHE_REFRESH(expiration))

    if remove_deleted:
      for varname in self.__cache__:
        if not varname in cached_properties:
          del self.__cache__[varname]

  def get_cache_ages(self):
    """Get the age of cached values.

    :rtype: dict
    
    Properties not yet cached will appear as ``None``.
    
    """
    ages = dict.fromkeys(self._get_cached_properties(), None)
    if self.__cache__:
      now = time()
      ages.update(dict(
        (k, now - v[1])
        for k, v in self.__cache__.items()
      ))
    return ages

  @classmethod
  def cached_property(cls, func):
    """Decorator that turns a class method into a cached property.

    :param func: bound method to be turned in to a property
    :type func: func

    A cached property acts similarly to a property but is only computed once
    and then stored in the instance's `__cache__` attribute along with the time
    it was last computed. Subsequent calls will read directly from the cached
    value.  To refresh several or all cached properties, use the
    :meth:`refresh_cache` method.

    Should only be used with methods of classes that inherit from ``Cacheable``.
    
    """
    return _CachedProperty(func)


class _CachedProperty(property):

  """Instance of a cached property for a model.

  Based on the emulation of PyProperty_Type() in Objects/descrobject.c from 
  http://infinitesque.net/articles/2005/enhancing%20Python's%20property.xhtml

  """

  def __init__(self, func):
    self.func = func
    self.__doc__ = func.__doc__

  def __get__(self, obj, objtype=None):
    if obj is None:
      return self
    else:
      try:
        return obj.__cache__[self.func.__name__][0]
      except (KeyError, TypeError):
        value = self.func(obj)
        self.__set__(obj, value)
        return value

  def __set__(self, obj, value):
    if not obj.__cache__:
      obj.__cache__ = {}
    if value:
      if isinstance(value, CACHE_REFRESH):
        if self.func.__name__ in obj.__cache__:
          age = time() - obj.__cache__[self.func.__name__][1]
          if age > value.expiration:
            obj.__cache__[self.func.__name__] = (self.func(obj), time())
        else:
          obj.__cache__[self.func.__name__] = (self.func(obj), time())
      else:
        obj.__cache__[self.func.__name__] = (value, time())
      try:
        # for persistent mutable caches, trigger refresh.
        obj.__cache__.changed()
      except AttributeError:
        pass

  def __delete__(self, obj):
    del obj.__cache__[self.func.__name__]

  def __repr__(self):
    return '<CachedProperty %r>' % self.func


# Query helpers
# =============

def query_to_models(query):
  """Returns the model classes associated with a query.
  
  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :rtype: list

  """
  if hasattr(query, 'attr'):
    # this is a subquery
    return [query.attr.target_mapper]
  else:
    # this is a main query
    return [
      d['expr'].class_
      for d in query.column_descriptions
      if isinstance(d['expr'], Mapper)
    ]

def query_to_dataframe(query, connection=None, columns=None, **kwargs):
  """Load a Pandas dataframe from an SQLAlchemy query.

  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :param connection: the connection to use to execute the query. By default
    the method will create a new connection using the session's bound engine
    and properly close it afterwards.
  :type connection: sqlalchemy.engine.base.Connection
  :param columns: a list of column names. If unspecified, the method will use
    the table's keys from the query's metadata. If the passed data do not have
    named associated with them, this argument provides names for the columns.
    Otherwise this argument indicates the order of the columns in the result
    (any names not found in the data will become all-NA columns)
  :type columns: list
  :rtype: pandas.DataFrame

  Any keyword arguments will be forwarded to `pandas.DataFrame.from_records`.
  The following are available:

    * exclude: a list of column names to exclude from the dataframe
    * index: the column to use as index
    * coerce_float: Attempt to convert values to non-string, non-numeric
      objects (like decimal.Decimal) to floating point.
  
  """
  connection = connection or query.session.get_bind()
  result = connection.execute(query.statement)
  columns = columns or result.keys()
  dataframe = DataFrame.from_records(
    result.fetchall(),
    columns=columns,
    **kwargs
  )
  result.close()
  return dataframe

def query_to_records(query, connection=None, use_labels=False):
  """Raw execute of the query into a generator.

  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :param connection: the connection to use to execute the query. By default
    the method will create a new connection using the session's bound engine
    and properly close it afterwards.
  :type connection: sqlalchemy.engine.base.Connection
  :param use_labels: whether or not to use labels instead of raw column names
    in the output dictionary. Useful when retrieving results from multiple
    tables with duplicate column names.
  :type use_labels: bool
  :rtype: generator

  About 5 times faster than loading the objects. Useful if only interested in
  raw columns of the model::

    # for ~300k models
    In [1]: %time [m.id for s in Model.q]
    CPU times: user 48.22 s, sys: 2.62 s, total: 50.84 s
    Wall time: 52.19 s
    In [2]: %time [m['id'] for s in query_to_records(Model.q)]
    CPU times: user 9.12 s, sys: 0.20 s, total: 9.32 s
    Wall time: 10.32 s
  
  """
  connection = connection or query.session.get_bind()
  selectable = query.statement
  if use_labels:
    selectable = selectable.apply_labels() 
  result = connection.execute(selectable)
  keys = result.keys()
  for record in result:
    yield {k:v for k, v in zip(keys, record)}
  result.close()


# Mutable columns
# ===============

class _JSONEncodedType(TypeDecorator):

  """Base class for storing python mutables as a JSON.

  For mutability tracking, associate with a Mutable.

  The underlying immutable object is of kind ``sqlalchemy.types.unicodetext``.
  Note that it has a character limit so care is needed when storing very large
  objects.


  """

  impl = UnicodeText

  def process_bind_param(self, value, dialect):
    return dumps(value) if value else None

  def process_result_value(self, value, dialect):
    raise NotImplementedError()


class JSONEncodedDict(_JSONEncodedType):

  """Implements dictionary column field type for SQLAlchemy.

  This can be used as a Column type during table creation::

    some_column_name = Column(JSONEncodedDict)

  It also implements limited  mutability tracking to know when to update the
  database: set, del and update actions are tracked. If another method to
  update the dictionary is used, it will not automatically flag the
  dictionary for update (for example if a deeply nested key is updated).
  In such a case, the ``changed`` method needs the be called manually
  after the operation.

  """

  def process_result_value(self, value, dialect):
    return loads(value) if value else {}


class _MutableDict(Mutable, dict):

  """Used with JSONEncoded dict to be able to track updates.

  This enables the database to know when it should update the stored string
  representation of the dictionary. This is much more efficient than naive
  automatic updating after each query.

  """

  @classmethod
  def coerce(cls, key, value):
    """Convert plain dictionaries to Features."""
    if not isinstance(value, cls):
      if isinstance(value, dict):
        return cls(value)
      return Mutable.coerce(key, value) # this will raise an error
    else:
      return value

  def update(self, *args, **kwargs):
    """Detect dictionary update events and emit change events."""
    dict.update(self, *args, **kwargs)
    self.changed()
    
  def __setitem__(self, key, value):
    """Detect dictionary set events and emit change events."""
    dict.__setitem__(self, key, value)
    self.changed()
    
  def __delitem__(self, key):
    """Detect dictionary del events and emit change events."""
    dict.__delitem__(self, key)
    self.changed()
    
_MutableDict.associate_with(JSONEncodedDict)


class JSONEncodedList(_JSONEncodedType):

  """Implements list column field type for SQLAlchemy.

  This can be used as a Column type during table creation::

    some_column_name = Column(JSONEncodedList)

  Currently only set, delete, append and extend events are tracked. Others
  will require a call to ``changed`` to be persisted.

  """

  def process_result_value(self, value, dialect):
    return loads(value) if value else []


class _MutableList(Mutable, list):

  """Used with JSONEncoded list to be able to track updates.

  This enables the database to know when it should update the stored string
  representation of the dictionary. This is much more efficient than naive
  automatic updating after each query.

  """

  @classmethod
  def coerce(cls, key, value):
    """Convert plain dictionaries to Features."""
    if not isinstance(value, cls):
      if isinstance(value, list):
        return cls(value)
      return Mutable.coerce(key, value) # this will raise an error
    else:
      return value

  def append(self, *args, **kwargs):
    """Detect update events and emit change events."""
    list.append(self, *args, **kwargs)
    self.changed()

  def extend(self, *args, **kwargs):
    """Detect update events and emit change events."""
    list.extend(self, *args, **kwargs)
    self.changed()
    
  def __setitem__(self, index, value):
    """Detect set events and emit change events."""
    list.__setitem__(self, index, value)
    self.changed()
    
  def __delitem__(self, index):
    """Detect del events and emit change events."""
    list.__delitem__(self, index)
    self.changed()

_MutableList.associate_with(JSONEncodedList)


# Flask view helpers
# ==================

class _ViewMeta(type):

  """To register classes with an app or blueprint on definition."""

  http_methods = frozenset(['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'PATCH'])

  def __new__(mcs, name, bases, dct):
    view_class = super(_ViewMeta, mcs).__new__(mcs, name, bases, dct)

    if view_class.rules:

      if not view_class.__app__:
        raise ValueError('%r is not bound to an app' % (view_class, ))

      rule_methods = set(
        meth for meths in view_class.rules.values() for meth in meths
      )
      invalid_methods = rule_methods - mcs.http_methods
      if invalid_methods:
        raise ValueError('Invalid rule methods: %s' % (invalid_methods, ))

      if view_class.endpoint is None:
        view_class.endpoint = uncamelcase(view_class.__name__)

      if view_class.methods is None:
        methods = set(key.upper() for key in dct) & mcs.http_methods
        view_class.methods = sorted(methods or [])
      
      view_class.register_view()

    return view_class


class View(_View):

  """Base view implementation that simplifies route registration.

  This class is very similar to :class:`flask.views.MethodView` but goes a 
  step further in registering its routes automatically. Rules are specified
  through the :prop:`rules` property.

  Usage::

    class MyView(View):

      __app__ = flask_app

      rules = {
        '/some_route': ['GET'],
        '/some_route/<some_index>': ['GET', 'POST']
      }

      def get(self, **kwargs):
        if kwargs:
          some_index = kwargs['some_index']
          # we are in the second route case
          # ...
        else:
          # we are in the first route case
          # ...

      def post(self, **kwargs):
        some_index = kwargs['some_index']
        # ...


  Typically, this view will be generated by the :func:`make_view` function,
  which will set the ``__app__`` attribute.
  
  """

  __metaclass__ = _ViewMeta

  #: The Flask application views should be bound to. If you are using the
  #: :func:`make_view` function, this attribute will be set automatically.
  __app__ = None

  #: The view endpoint. This can generally be skipped, it is only used
  #: internally by Flask in the routes dictionary. If not specifies, it will
  #: default to the class' name uncamelcased.
  endpoint = None

  #: If specified, only these methods will be allowed. This can be useful if
  #: subclassing views to override the rule methods.
  methods = None

  #: A dictionary with the rules to create. Each key is the url rule and the
  #: corresponding value a list of methods to accept. E.g.
  #: ``{'/index/': ['GET'], '/index/<page>': ['GET', 'PUT']}``.
  rules = None

  @classmethod
  def register_view(cls):
    """Attach view to app or blueprint.
    
    Called by the metaclass when the class is created.
    
    """
    if cls.rules is None:
      raise ValueError('No rules found for %r' % (cls, ))

    view = cls.as_view(cls.endpoint)
    allowed_methods = set(cls.methods)
    for rule, methods in cls.rules.items():
      methods = set(methods) & allowed_methods
      if methods:
        cls.__app__.add_url_rule(rule=rule, view_func=view, methods=methods)
      
  def dispatch_request(self, **kwargs):
    """Dispatches requests to the corresponding method name.
    
    Similar to the :class:`flask.views.MethodView` implementation: GET requests
    are passed to :meth:`get`, POST to :meth:`post`, etc.
    
    """
    meth = getattr(self, request.method.lower(), None)
    if meth is None and request.method == 'HEAD':
      meth = getattr(self, 'get', None)
    return meth(**kwargs)


def make_view(app, view_class=View, view_name='View', **kwargs):
  """Create a base View class bound to the Flask application.

  :param app: the app (or blueprint) to be bound to
  :type app: Flask app or blueprint
  :param view_class: base view class
  :type view_class: kit.util.View
  :param view_name: the name of the class created. If multiple base views are
    generated, you can specify a different name for each using this argument.
  :type view_name: str
  :rtype: kit.util.View

  Any keyword arguments will be added to the class' dictionary. This is only
  provided as a convenience, if many methods are added, it is simpler to
  subclass :class:`kit.util.View` directly rather than use this function.

  """
  kwargs.update({'__app__': app})
  return type(view_name, (view_class, ), kwargs)
