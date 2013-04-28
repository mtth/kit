#!/usr/bin/env python

"""Utility module."""

from datetime import datetime
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
  s1 = sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
  return sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

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
  if isinstance(value, list):
    return [to_json(v, depth) for v in value]
  if isinstance(value, (float, int, long, str, unicode, tuple)):
    return value
  if value is None:
    return None
  if isinstance(value, datetime):
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
    rv = {}
    if depth < 1:
      return rv
    for varname in self.__json__:
      try:
        rv[varname] = to_json(getattr(self, varname), depth)
      except ValueError as e:
        rv[varname] = e.message
    return rv


class Loggable(object):

  """Convenient logging mixin.

  This implements the main logging methods directly on the class instance. For
  example, this allows something like::

    instance.info('Some message.')

  The instance's ``__str__`` is prepended to the message for easier debugging.

  Note that this class doesn't override `` __getattr__`` to preserve exception
  context. Otherwise the line where the inexistent attribute was accessed will
  be lost.

  """

  __logger__ = None

  def _logger(self, message, loglevel):
    if not self.__logger__:
      self.__logger__ = getLogger(self.__module__)
    action = getattr(self.__logger__, loglevel)
    return action('%s :: %s' % (self, message))

  def debug(self, message):
    """Debug level message."""
    return self._logger(message, 'debug')

  def info(self, message):
    """Info level message."""
    return self._logger(message, 'info')

  def warn(self, message):
    """Warn level message."""
    return self._logger(message, 'warn')

  def error(self, message):
    """Error level message."""
    return self._logger(message, 'error')


class Cacheable(object):

  """Mixin to support cacheable properties.
  
  Implements a few cache maintenance utilities.
  
  """

  _cache = None

  def _get_cached_properties(self):
    return [
        varname
        for varname in dir(self.__class__)
        if isinstance(getattr(self.__class__, varname), _CachedProperty)
    ]

  def refresh_cache(self, names=None, expiration=0, remove_deleted=True):
    """Refresh cached properties.

    :param names: list of cached property names to refresh. If specified, only
      these will be refreshed.
    :type names: iterable
    :param expiration: if specified, only properties of age greater than this
      value will be refreshed.
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
          setattr(self, name, _CacheRefresh(expiration))
        else:
          raise AttributeError('No cached property %r on %r.' % (name, self))
    else:
      for varname in cached_properties:
        setattr(self, varname, _CacheRefresh(expiration))

    if remove_deleted:
      for varname in self._cache:
        if not varname in cached_properties:
          del self._cache[varname]

    try:
      self._cache.changed()
    except:
      pass

  def view_cache(self):
    """Get the age of cached values.

    :rtype: dict
    
    Properties not yet cached will appear as ``None``.
    
    """
    rv = dict.fromkeys(self._get_cached_properties(), None)
    if self._cache:
      now = time()
      rv.update(dict(
        (k, now - v[1])
        for k, v in self._cache.items()
      ))
    return rv

  @classmethod
  def cached_property(cls, func):
    """Decorator that turns a class method into a cached property.

    :param func: bound method to be turned in to a property
    :type func: func

    A cached property acts similarly to a property but is only computed once and
    then stored in the instance's ``_cache`` attribute along with the time it was
    last computed. Subsequent calls will read directly from the cached value.  To
    refresh several or all cached properties, use the ``refresh_cache`` method.

    Should only be used with methods of classes that inherit from ``Cacheable``.
    
    """
    return _CachedProperty(func)


class _CacheRefresh(object):

  """Special class used to trigger cache refreshes."""

  def __init__(self, expiration):
    self.expiration = expiration


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
        return obj._cache[self.func.__name__][0]
      except (KeyError, TypeError) as e:
        value = self.func(obj)
        self.__set__(obj, value)
        return value

  def __set__(self, obj, value):
    if not obj._cache:
      obj._cache = {}
    if value:
      if isinstance(value, _CacheRefresh):
        if self.func.__name__ in obj._cache:
          t = time() - obj._cache[self.func.__name__][1]
          if t > value.expiration:
            obj._cache[self.func.__name__] = (self.func(obj), time())
        else:
          obj._cache[self.func.__name__] = (self.func(obj), time())
      else:
        obj._cache[self.func.__name__] = (value, time())
      try:
        obj._cache.changed()
      except:
        pass

  def __delete__(self, obj):
    del obj._cache[self.func.__name__]

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

def query_to_dataframe(query, connection=None, exclude=None, index=None,
                       columns=None, coerce_float=False):
  """Load a Pandas dataframe from an SQLAlchemy query.

  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :param connection: the connection to use to execute the query. By default
    the method will create a new connection using the session's bound engine
    and properly close it afterwards.
  :type connection: sqlalchemy.engine.base.Connection
  :param exclude: a list of column names to exclude from the dataframe
  :type exclude: list
  :param index: the column to use as index
  :type index: str
  :param names: a list of column names. If unspecified, the method will use
    the table's keys from the query's metadata. If the passed data do not have
    named associated with them, this argument provides names for the columns.
    Otherwise this argument indicates the order of the columns in the result
    (any names not found in the data will become all-NA columns)
  :type names: list
  :param coerce_float: Attempt to convert values to non-string, non-numeric
    objects (like decimal.Decimal) to floating point.
  :type coerce_float: bool
  :rtype: pandas.DataFrame
  
  """
  connection = connection or query.session.get_bind()
  exclude = exclude or []
  result = connection.execute(query.statement)
  columns = columns or result.keys()
  dataframe = DataFrame.from_records(
    result.fetchall(),
    columns=columns,
    exclude=exclude,
    index=index,
    coerce_float=coerce_float,
  )
  result.close()
  return dataframe

def query_to_records(query, connection=None):
  """Raw execute of the query into a generator.

  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :param connection: the connection to use to execute the query. By default
    the method will create a new connection using the session's bound engine
    and properly close it afterwards.
  :type connection: sqlalchemy.engine.base.Connection
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
  result = connection.execute(query.statement)
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

  http_methods = ['get', 'post', 'put', 'delete', 'patch']

  def __new__(mcs, name, bases, dct):
    view_class = super(_ViewMeta, mcs).__new__(mcs, name, bases, dct)

    if view_class.rules:

      if not view_class.__app__:
        raise ValueError('%r is not bound to an app' % (view_class, ))

      if view_class.endpoint is None:
        view_class.endpoint = uncamelcase(view_class.__name__)

      if view_class.methods is None:
        methods = set(key.upper() for key in dct if key in mcs.http_methods)
        view_class.methods = sorted(methods or [])
      
      view_class.register_view(view_class.__app__)

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

  #: If specified, only these methods will have their routes registered. This
  #: can be useful if subclassing views.
  methods = None

  #: A dictionary with the rules to create. Each key is the url rule and the
  #: corresponding value a list of methods to accept. E.g.
  #: ``{'/index': ['GET'], '/index/<page>': ['GET', 'PUT']}``.
  rules = None

  @classmethod
  def register_view(cls, app):
    """Attach view to app or blueprint.
    
    Called by the metaclass when the class is created.
    
    """
    view = cls.as_view(cls.endpoint)

    all_methods = set(cls.methods)
    if cls.rules is None:
      raise ValueError('No rules found for %r' % (cls, ))
    for rule, methods in cls.rules.items():
      rule_methods = set(methods) & all_methods
      if rule_methods:
        app.add_url_rule(rule=rule, view_func=view, methods=rule_methods)
      
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
