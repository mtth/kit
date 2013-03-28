#!/usr/bin/env python

"""General helpers."""

from collections import defaultdict, Mapping, namedtuple
from copy import deepcopy
from ConfigParser import SafeConfigParser
from csv import DictReader
from datetime import datetime
from decimal import Decimal
from itertools import islice
from json import dumps, loads
from logging import getLogger
from math import ceil
from re import sub
from sqlalchemy.orm import Query
from time import time

try:
  from pandas import DataFrame, Series
except ImportError:
  pass


Part = namedtuple('Part', ['offset', 'limit'])

def partition(collection, parts=0, size=0):
  """Split an iterable into several pieces.

  :param collection: the iterable that will be partitioned. Note that
    ``partition`` needs to be able to compute the total length of the iterable
    so generators won't work.
  :type collection: list, query or file
  :param parts: number of parts to split the collection into
  :type parts: int
  :param size: number of items (lines if ``collection`` is a file) per
    part
  :type size: int
  :rtype: generator

  Only one of ``parts`` and ``size`` can be specified at a time.

  ``partition`` returns a generator that yields a tuple ``(batch, part)``
  on each iteration. ``batch`` is of the same type as ``collection``, filtered
  to the corresponding partition and ``part`` is a named tuple with two 
  properties:

  * ``offset``, the first index of the partition (if ``collection`` is a file
    it will be the first line number instead)
  * ``limit``, the max-length of the partition (the last one might be shorter)

  """
  if (parts and size) or (not parts and not size):
    raise ValueError('Exactly one of parts and size must be specified.')
  offset = 0
  limit = size
  if isinstance(collection, Query):
    # collection is a SQLAlchemy query
    # count won't be very efficient, but only run once so it's ok
    total = collection.count()
    if parts:
      limit = int(ceil(float(total) / parts))
    while offset < total:
      yield collection.offset(offset).limit(limit), Part(offset, limit)
      offset += limit
  elif isinstance(collection, list):
    total = len(collection)
    if parts:
      limit = int(ceil(float(total) / parts))
    while offset < total:
      yield collection[offset:offset + limit], Part(offset, limit)
      offset += limit
  elif isinstance(collection, file):
    total = sum(1 for line in collection)
    if parts:
      limit = int(ceil(float(total) / parts))
    while offset < total:
      collection.seek(0)
      yield islice(collection, offset, offset+limit), Part(offset, limit)
      offset += limit

def convert(value, rtype=None, allow_json=False):
  """Converts a string to another value.

  :param value: the value to be converted
  :type value: str
  :param rtype: string representation of the type the value should be
    converted to. Accepted values are ``['int', 'float', 'bool', 'unicode',
    'str', 'json']``.
  :type rtype: str
  :param allow_json: allow loading of json strings
  :type allow_json: bool
  :rtype: int, float, bool, str, unicode

  If ``rtype`` isn't specified, the following conversions are attempted in
  order: ``int``, ``float``, ``bool`` and finally ``json.loads`` (only if
  ``allow_json`` is ``True``). If all fail, the method returns the
  string ``value`` unchanged.

  Boolean conversions convert ``'true', '1'`` to ``True``, and ``'false', '0'``
  to ``False`` (case insensitive) and otherwise raises an error.

  """
  value = value.strip()
  if rtype:
    if rtype == 'int':
      return int(value)
    elif rtype == 'float':
      return float(value)
    elif rtype == 'bool':
      if value.lower() == 'true' or value == '1':
        return True
      elif not value or value.lower() == 'false' or value == '0':
        return False
      else:
        raise ValueError('Can\'t convert %s to boolean.' % value)
    elif rtype == 'unicode':
      return unicode(value, encoding='utf-8', errors='replace')
    elif rtype == 'str':
      return value
    elif rtype == 'json':
      return loads(value)
    # if we get here, something has gone wrong
    raise ValueError('Invalid conversion type: %s' % rtype)
  else:
    try:
      return int(value)
    except ValueError:
      try:
        return float(value)
      except ValueError:
        if value.lower() == 'true':
          return True
        elif value.lower() == 'false':
          return False
        elif value == 'None':
          return None
        else:
          if allow_json:
            try:
              return loads(value)
            except ValueError:
              pass
          return value

def prod(iterable, key=None):
  """Cumulative product function (the equivalent of ``sum``).

  :param key: function called on each element of the iterable, if none then
    identity is assumed
  :type key: callable
  :rtype: int, float

  """
  rv = 1
  for elem in iterable:
    if key is None:
      rv *= elem
    else:
      rv *= key(elem)
  return rv

def uncamelcase(name):
  """Transforms CamelCase to underscore_case.

  :param name: string input
  :type name: str
  :rtype: str
  
  """
  s1 = sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
  return sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def parse_config(file_or_filepath, default=None, allow_json=False,
  case_sensitive=False, parser_type=SafeConfigParser):
  """Returns a dictionary of values from a configuration file.

  :param file_or_filepath: file or filepath to configuration file
  :type file_or_filepath: str or file
  :param default: dictionary of default values to use
  :type default: dict
  :param allow_json: allow loading of json options
  :type allow_json: bool
  :param case_sensitive: keep option names' case
  :type case_sensitive: bool
  :param parser_type: base parser type to use for parsing the file
  :type parser_type: ConfigParser.RawConfigParser
  :rtype: dict

  """
  parser = parser_type()
  if case_sensitive:
    parser.optionxform = str
  if isinstance(file_or_filepath, str):
    with open(file_or_filepath) as f:
      parser.readfp(f)
  else:
    parser.readfp(file_or_filepath)
  conf = {
    s: {
      k: convert(v, allow_json=allow_json)
      for (k, v) in parser.items(s)
    }
    for s in parser.sections()
  }
  if default:
    conf = dict_update(default, conf, copy=True)
  return conf

def to_json(value, depth=1):
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
  try:
    if isinstance(value, DataFrame):
      return [ 
        {str(colname): row[i] for i, colname in enumerate(value.columns)}
        for row in value.values
      ]
  except NameError: # pandas missing
    pass
  raise ValueError('not jsonifiable')

def exponential_smoothing(data, alpha=0.5):
  """Smoothing data.

  :param data: list of tuples. The smoothing will be done on
    the first item of each tuple.
  :type data: ``list``
  :param alpha: the discount factor
  :type alpha: ``float``
  :rtype: ``list``
  
  """
  sorted_data = sorted(data, key=lambda e: e[0])
  return [(x, sum(_y * alpha ** (x - _x) for (_x, _y) in sorted_data[:i+1])
        / sum(alpha ** (x - _x) for (_x, _y) in sorted_data[:i+1]))
      for i, (x, y) in enumerate(sorted_data)]

def histogram(data, key=None, bins=50, restrict=None, categories=None,
              order=0, expand=False):
  """Returns a histogram of counts for the data.

  :param data: the data to be binned
  :type data: iterable of tuples
  :param restrict: if provided, only data elements which return `True`
    will be included in the histogram. Default is `None` (all elements
    are included).
  :type restrict: function or None
  :param categories: if provided, elements will be counted in separate
    categories. This changes the format of the output to a dictionary
    with the different categories as keys in each bin.
  :type categories: function or None
  :param bins: either an int (total number of bins, which will be 
    uniformly spread) or a list of increasing bin values. smaller
    values will be in the first bin, larger in the last one.
  :type bins: int or list(int)
  :param order: 0 if data isn't sorted, 1 if sorted in ascending, -1 if
    sorted in descending order.
  :type order: string
  :rtype: dict

  Possible extension: allow categories to return a list of keys, which would
  allow elements to be included in several counts.

  """
  key = key or (lambda e: e)
  if isinstance(bins, int):
    n_bins = bins
    if not n_bins > 0: raise Exception("Number of bins must be > 0.")
    if order == '1':
      max_value = key(data[-1])
      min_value = key(data[0])
    elif order == '-1':
      max_value = key(data[0])
      min_value = key(data[-1])
    else:
      max_value = max(key(e) for e in data)
      min_value = min(key(e) for e in data)
    if n_bins == 1 or max_value == min_value:
      # If everything is equal, or just one bin, return one bin. Duh.
      return {min_value: len(data)}
    else:
      bin_width = float(max_value - min_value) / n_bins
      bins = [min_value + float(i) * bin_width for i in xrange(n_bins)]
      def find_bin(e):
        # this is faster than default iterating over bins
        index = min(int((key(e) - min_value) / bin_width), n_bins - 1)
        return bins[index]
  else:
    if len(bins) == 1:
      # not very interesting but for compatibility
      return {bins[0]: len(data)}
    def find_bin(a):
      # default bin iterator
      if a < bins[0]:
        return bins[0]
      for bin in reversed(bins):
        if a >= bin:
          return bin
  if categories is None:
    data_histogram = dict.fromkeys(bins, 0)
    for e in data:
      if restrict is None or restrict(e):
        data_histogram[find_bin(key(e))] += 1
    return data_histogram
  else:
    data_histogram = defaultdict(lambda: defaultdict(int))
    for e in data:
      if restrict is None or restrict(e):
        data_histogram[find_bin(key(e))][categories(e)] += 1
    data_histogram = dict(
      (k, dict(v)) for (k, v) in data_histogram.iteritems()
    )
    if expand:
      keys = set(key for v in data_histogram.values() for key in v.keys())
      data_histogram = dict(
          (
            key,
            dict((k, v.get(key, 0)) for (k, v) in data_histogram.iteritems())
          )
          for key in keys
      )
    return data_histogram

def dict_depth(dct):
  """Depth of a dictionary.

  :param dct: dictionary
  :type dct: dict
  :rtype: int
  
  """
  values = [
      value
      for value in dct.itervalues()
      if isinstance(value, dict)
  ]
  return max(dict_depth(value) for value in values) + 1 if values else 1

def dict_width(dct):
  """Width of a dictionary.

  :param dct: dictionary
  :type dct: dict
  :rtype: int
  
  """
  values = [
      value
      for value in dct.itervalues()
      if isinstance(value, dict)
  ]
  return sum(dict_width(value) for value in values) + len(dct) - len(values)

def dict_flatten(dct, sep='_', prefix=''):
  """Flatten a dictionary.

  :param dct: dictionary
  :type dct: dict
  :param sep: the separator used when concatenating keys
  :type sep: str
  :param prefix: a prefix to add to all new keys
  :type prefix: str
  :rtype: dict:

  .. note::

    All keys in the dictionary must be strings.

  """
  items = []
  for key, value in dct.iteritems():
    k = prefix + sep + key if prefix else key
    if isinstance(value, dict) and value:
      items.extend(dict_flatten(value, sep, k).items())
    else:
      items.append((k, value))
  return dict(items)

def dict_unflatten(dct, sep='_', cname='all'):
  """Unflatten a dictionary.

  :param dct: dictionary
  :type dct: dict
  :param sep: the separator used to split keys
  :type sep: str
  :param cname: a key name used when a value would be added on an already
    expanded dictionary. A simple example is when trying to unflatten 
    ``{'a': 1, 'a_b': 2}``: there is ambiguity on where to store the value
    for key ``'a'`` because it already contains the dictionary ``{'b': 2}``.
    This is resolved creating a new key ``cname`` in this latter dictionary.
  :type cname: str
  :rtype: dict:

  """
  result = {}
  keys = []
  for key in dct.iterkeys():
    keys.append(key.split(sep))
  keys.sort(key=len, reverse=True)
  for key in keys:
    d = result
    for part in key[:-1]:
      if part not in d:
        d[part] = {}
      d = d[part]
    if key[-1] in d:
      d[key[-1]][cname] = dct[sep.join(key)]
    else:
      d[key[-1]] = dct[sep.join(key)]
  return result

def dict_update(a, b, copy=False):
  """Update for nested dictionaries.

  :param copy: whether or not to do a deepcopy of the dictionary before
    updating.
  :type copy: bool
  :rtype: dict

  """
  if copy:
    a = deepcopy(a)
  for k, v in b.iteritems():
    if isinstance(v, Mapping):
      a[k] = dict_update(a.get(k, {}), v)
    else:
      a[k] = b[k]
  return a

def dict_table(mode='horizontal', left_columns=None):
  """To create nested HTML table headers.

  Not functional anymore.
  
  """
  items = []
  unflattened = Dict(self.unflattened())
  depth = unflattened.depth()
  width = unflattened.width()
  if mode == 'horizontal':
    levels = defaultdict(list)
    for key in sorted(self.flattened().iterkeys()):
      parts = key.split(self.sep)
      for index, part in enumerate(parts[:-1]):
        levels[index].append([part, 1, 1, self.sep.join(parts[:(index + 1)])])
      levels[len(parts) - 1].append([parts[-1], depth - len(parts) + 1, 1, key])
    for index, level in levels.items():
      if index == 0 and left_columns:
        row = [[column, depth, 1, column] for column in left_columns]
      else:
        row = []
      current_label = None
      for label, height, width, full_label in level:
        if label == current_label:
          row[-1][2] += 1
        else:
          current_label = label
          row.append([label, height, width, full_label])
      items.append(row)
  elif mode == 'vertical':
    indices = {}
    for i, key in enumerate(sorted(self.flattened().iterkeys())):
      if i == 0 and left_columns:
        row = [[column, width, 1, column] for column in left_columns]
      else:
        row = []
      parts = key.split(self.sep)
      k = 0
      for j, part in enumerate(parts[:-1]):
        full_label = self.sep.join(parts[:(j + 1)])
        if not full_label in indices:
          indices[full_label] = (i, k)
          row.append([part, 1, 1, full_label])
          k += 1
        else:
          a, b = indices[full_label]
          items[a][b][1] += 1
      indices[key] = (i, k)
      row.append([parts[-1], 1, depth - len(parts) + 1, key])
      items.append(row)
  return items


class SmartDictReader(DictReader):

  """``DictReader`` with built-in value conversion.

  :param csvfile: open file instance.
  :type csvfile: file
  :param fields: list of ``fieldnames`` or list of tuples
    ``(fieldname, fieldtype)``. If specified, the ``fieldtype`` will be passed
    as second argument to the ``convert`` function.
  :type fields: list
  :param silent: whether or not to silence errors while processing the file.
  :type silent: bool
  :param allow_json: allow loading of json strings
  :type allow_json: bool
  :param kwargs: keyword arguments to forward to the undelying
    ``csv.DictReader`` object.
  :rtype: iterable

  Interesting values for kwargs can be:

  * delimiter = '\t'
  * quotechar = '\x07'

  The following attributes are also available:

  * ``rows_imported``, the total number of rows successfully imported
  * ``errors``, a list of tuples ``(e, row)`` where ``e`` is error and ``row``
    the full row for each error raised

  """

  def __init__(self, csvfile, fields=None, silent=False, allow_json=False,
               **kwargs):
    self.csvfile = csvfile
    self.rows_imported = 0
    self.errors = []
    self.silent = silent
    self.allow_json = allow_json
    if fields:
      if isinstance(fields[0], (list, tuple)):
        kwargs['fieldnames'] = [field[0] for field in fields]
        self.field_types = dict(fields)
      else:
        kwargs['fieldnames'] = fields
        self.field_types = dict.fromkeys(fields, None)
      DictReader.__init__(self, csvfile, **kwargs)
    else:
      DictReader.__init__(self, csvfile, **kwargs)
      self.field_types = dict.fromkeys(self.fieldnames, None)

  def next(self):
    row = DictReader.next(self)
    try:
      processed_row = dict(
          (key, convert(value, self.field_types[key], self.allow_json))
          for key, value in row.iteritems()
      )
    except ValueError as e:
      self.errors.append((e, row))
      if not self.silent:
        raise e
    else:
      self.rows_imported += 1
      return processed_row


class RunningStat(object):

  """ To compute running means and variances efficiently.

  Usage::

    rs = RunningStat()
    for i in range(10):
      rs.push(i)
    rs.var

  """

  def __init__(self):
    self.count = 0
    self._mean = float(0)
    self.unweighted_variance = float(0)

  def __repr__(self):
    return '<RunningStat (count=%s, avg=%s, sdv=%s)>' % (
      self.count, self.avg, self.sdv
  )

  @property
  def avg(self):
    """Current mean."""
    if self.count > 0:
      return self._mean
    return 0

  @property
  def var(self):
    """Current variance."""
    if self.count > 1:
      return self.unweighted_variance/(self.count-1)
    return 0

  @property
  def sdv(self):
    """Current standard deviation."""
    return self.var ** 0.5

  def push(self, n):
    """Add a new element to the statistic.

    :param n: number to add
    :type n: int, float

    """
    if n == None:
      return
    self.count += 1
    if self.count == 1:
      self._mean = float(n)
      self.unweighted_variance = float(0)
    else:
      mean = self._mean
      s = self.unweighted_variance
      self._mean = mean + (n - mean) / self.count
      self.unweighted_variance = s + (n - self._mean) * (n - mean)


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

