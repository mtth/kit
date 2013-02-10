#!/usr/bin/env python

"""General helpers."""

from collections import defaultdict
from csv import DictReader
from datetime import datetime
from json import dumps, loads
from functools import partial, wraps
from re import sub
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, UnicodeText
from time import time


# Utility functions

def prod(iterable, key=None):
  """Helper function for cumulative products.

  :param key: function called on each element of the iterable, if none then
    identity is assumed
  :type key: callable
  :param restrict: if provided, elements where restrict(element) is True
    will not be included
  :type restrict: callable

  """
  rv = 1
  for index, elem in enumerate(iterable):
    if key is None:
      rv *= elem
    else:
      rv *= key(elem)
  return rv

def uncamelcase(name):
  """Transform CamelCase to underscore_case."""
  s1 = sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
  return sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def convert(value, return_type=None):
  """Converts a string to a boolean, int or float."""
  value = value.strip()
  if return_type:
    if return_type == 'int':
      return int(value)
    elif return_type == 'float':
      return float(value)
    elif return_type == 'bool':
      if value.lower() == 'true' or value == '1':
        return True
      elif not value or value.lower() == 'false' or value == '0':
        return False
      else:
        raise ValueError('Can\'t convert %s to boolean.' % value)
    elif return_type == 'unicode':
      return unicode(value, encoding='utf-8', errors='replace')
    elif return_type == 'str':
      return value
    # if we get here, something has gone wrong
    raise ValueError('Invalid conversion type: %s' % return_type)
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
        else:
          return value


# Utility Classes

class Dict(dict):

  """Dictionary class with a few helper methods.

  The goal of this class is to make multilevel dictionary actions
  simple.

  Usage::

    d = Dict(d)
    d.flattened()

  :param cname: key used when unflattening a dictionary and a key with a
    value also becomes a branch
  :type cname: string
  :param sep: the separator used to separate hierarchy levels
  :type sep: string

  """

  cname = 'all'
  sep = '_'

  def depth(self):
    """Depth of a dictionary."""
    values = [
        Dict(value)
        for value in self.itervalues()
        if isinstance(value, dict)
    ]
    return max(value.depth() for value in values) + 1 if values else 1

  def width(self):
    """Width of a dictionary."""
    values = [
        Dict(value)
        for value in self.itervalues()
        if isinstance(value, dict)
    ]
    return sum(value.width() for value in values) + len(self) - len(values)

  def table(self, mode='horizontal', left_columns=None):
    """For HTML headers mostly."""
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

  def flattened(self):
    """Flattened representation of the dictionary."""
    return self.__class__.flatten(self)

  def unflattened(self):
    """Unflattened representation of the dictionary."""
    return self.__class__.unflatten(self)

  @classmethod
  def flatten(cls, dic, sep=None, prefix=''):
    """Flatten. Classmethod for convenience."""
    sep = sep if sep else cls.sep
    items = []
    for key, value in dic.iteritems():
      k = prefix + sep + key if prefix else key
      if isinstance(value, dict) and value:
        items.extend(cls.flatten(value, sep, k).items())
      else:
        items.append((k, value))
    return dict(items)

  @classmethod
  def unflatten(cls, dic, sep=None, cname=None):
    """Unflatten. Classmethod for convenience"""
    sep = sep if sep else cls.sep
    cname = cname if cname else cls.cname
    result = {}
    keys = []
    for key in dic.iterkeys():
      keys.append(key.split(sep))
    keys.sort(key=len, reverse=True)
    for key in keys:
      d = result
      for part in key[:-1]:
        if part not in d:
          d[part] = {}
        d = d[part]
      if key[-1] in d:
        d[key[-1]][cname] = dic[sep.join(key)]
      else:
        d[key[-1]] = dic[sep.join(key)]
    return result

class SmartDictReader(DictReader):

  """Helper for importing .csv files.

  :param csvfile: open file instance
  :type csvfile: ``file``
  :param fields: list of fieldnames or list of tuples (fieldname, fieldtype)
  :rtype: iterable

  Interesting values for kwargs can be:
  * delimiter = '\t'
  * quotechar = '\x07'

  """

  def __init__(self, csvfile, fields=None, silent=False, **kwargs):
    self.csvfile = csvfile
    self.rows_imported = 0
    self.errors = []
    self.silent = silent
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
          (key, convert(value, self.field_types[key]))
          for key, value in row.iteritems()
      )
    except ValueError as e:
      self.errors.append((e, row))
      if not self.silent:
        raise e
    else:
      self.rows_imported += 1
      return processed_row


# Caching

def cached_property(func):
  return _CachedProperty(func)

class Cacheable(object):

  """Adds a few cache maintenance utilities."""

  def _get_cached_properties(self):
    return [
        varname
        for varname in dir(self.__class__)
        if isinstance(getattr(self.__class__, varname), _CachedProperty)
    ]

  def refresh_cached_property(self, name, expiration=0):
    setattr(self, name, _CacheRefresh(expiration))

  def refresh_all_cached_properties(self, expiration=0):
    for varname in self._get_cached_properties():
      setattr(self, varname, _CacheRefresh(expiration))

class _CacheRefresh(object):

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
    """Gets the value from cache (creating and refreshing as necessary)."""
    if obj is None:
      return self
    else:
      if not obj._cache or not self.func.__name__ in obj._cache:
        return None
      return obj._cache[self.func.__name__][0]

  def __set__(self, obj, value):
    """Sets the value in the cache.

    If the _cache is a JSONEncodedDict, this will also mark the dictionary
    as changed.
    
    """
    if not hasattr(obj, '_cache') or not obj._cache:
      obj._cache = {}
    if value:
      if isinstance(value, _CacheRefresh):
        t = time() - obj._cache[self.func.__name__][1]
        if t > value.expiration:
          obj._cache[self.func.__name__] = (self.func(obj), time())
      else:
        obj._cache[self.func.__name__] = (value, time())
      try:
        obj._cache.changed()
      except:
        pass

  def __repr__(self):
    return '<CachedProperty %r>' % self.func


# Jsonifification

def _jsonify(value, depth=0):
  if hasattr(value, 'jsonify'):
    return value.jsonify(depth=depth - 1)
  if isinstance(value, dict):
    return dict((k, jsonify(v, depth)) for k, v in value.items())
  if isinstance(value, list):
    return [jsonify(v, depth) for v in value]
  if isinstance(value, (float, int, long, str, unicode, tuple)):
    return value
  if isinstance(value, datetime):
    return str(value)
  if value is None:
    return None
  raise ValueError('not jsonifiable')

class Jsonifiable(object):

  """For easy API calls.

  This is depth first (different from the one in the ExpandedBase class).

  We keep track of what has already been jsonified. There might still be
  some repetition given that we do not control the order of exploration.
  If a key is revisited at a lower depth, it will be reparsed to allow for
  more exploration.

  """

  @property
  def _json_attributes(self):
    """Default implementation of the attributes to jsonify.

    This is relatively slow (because it is evaluated for each jsonify call).
    Consider overwriting it for better performance.
    
    """
    return [
      varname for varname in dir(self)
      if not varname.startswith('_')
      if not hasattr(getattr(self, varname), '__call__')
    ]

  def jsonify(self, depth=0):
    """Returns all keys and properties of an instance in a dictionary.

    Overrides the basic jsonify method to specialize it for models.

    This function minimizes the number of lookups it does (no dynamic
    type checking on the properties for example) to maximize speed.

    :param depth:
    :type depth: int
    :rtype: dict

    """
    rv = {}
    for varname in self._json_attributes:
      try:
        rv[varname] = _jsonify(getattr(self, varname), depth)
      except ValueError as e:
        rv[varname] = e.message
    return rv


# Logging

class Loggable(object):

  """To easily log stuff.

  This implements the main logging methods ('debug', 'info', 'warn', 'error')
  directly on the class instance. For example, this allows something like::

    instance.log('Some message.')

  Not using __getattr__ to preserve exception context. Otherwise the line where
  the inexistent attribute was accessed will be lost.

  """

  def _logger(self, message, loglevel):
    if not hasattr(self, '__logger__'):
      self.__logger__ = getLogger(self.__module__)
    action = getattr(self.__logger__, loglevel)
    return action('%s :: %s' % (self, message))

  def debug(self, message):
    return self._logger(message, 'debug')

  def info(self, message):
    return self._logger(message, 'info')

  def warn(self, message):
    return self._logger(message, 'warn')

  def error(self, message):
    return self._logger(message, 'error')


# SQLAlchemy Mutables

class JSONEncodedDict(TypeDecorator):

  """Represents an immutable structure as a JSON encoded dict.

  This can be used as a Column type during table creation::

    some_column_name = Column(JSONEncodedDict)

  .. note::

    There is a character limit in the UnicodeText field of the database
    so care is needed when storing very large dictionaries.

  """

  impl = UnicodeText

  def process_bind_param(self, value, dialect):
    return dumps(value) if value else None

  def process_result_value(self, value, dialect):
    return loads(value) if value else {}

class _MutableDict(Mutable, dict):

  """Used with JSONEncoded dict to be able to track updates.

  This enables the database to know when it should update the stored string
  representation of the dictionary. This is much more efficient than naive
  automatic updating after each query.

  .. note::

    Only set, del and update actions are tracked. If another method to
    update the dictionary is used, it will not automatically flag the
    dictionary for update (for example if a deeply nested key is updated).
    In such a case, the ``changed`` method needs the be called manually
    after the operation.

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


# Computations

class RunningStatistic(object):

  """ To compute running statistics efficiently."""

  def __init__(self):
    self.count = 0
    self.mean = float(0)
    self.unweighted_variance = float(0)

  def push(self, n):
    if n == None:
      return
    self.count += 1
    if self.count == 1:
      self.mean = float(n)
      self.unweighted_variance = float(0)
    else:
      mean = self.mean
      s = self.unweighted_variance
      self.mean = mean + (n - mean) / self.count
      self.unweighted_variance = s + (n - self.mean) * (n - mean)

  def variance(self):
      if self.count>1:
        return self.unweighted_variance/(self.count-1)
      return 0

def exponential_smoothing(data, alpha=0.5):
  """Helper function for smoothing data.

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

def histogram(data, key=lambda a: a, bins=50, restrict=None, categories=None,
              order=0, expand=False):
  """Returns a histogram of counts for the data.

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

  Possible extension: allow categories to return a list of keys, which would
  allow elements to be included in several counts.

  """
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
    data_histogram = dict((k, dict(v)) for (k, v) in data_histogram.iteritems())
    if expand:
      keys = set(key for v in data_histogram.values() for key in v.keys())
      data_histogram = dict(
          (key, dict((k, v.get(key, 0)) for (k, v) in data_histogram.iteritems()))
          for key in keys
      )
    return data_histogram

