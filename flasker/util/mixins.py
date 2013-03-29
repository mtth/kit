#!/usr/bin/env python

from logging import getLogger
from time import time

from .helpers import to_json


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

  def _logger(self, message, loglevel):
    if not hasattr(self, '__logger__'):
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

  def __repr__(self):
    return '<CachedProperty %r>' % self.func

