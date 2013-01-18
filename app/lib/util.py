#!/usr/bin/env python

"""Flask App Template helpers"""

from collections import defaultdict
from csv import DictReader
from datetime import datetime
from flask import jsonify, request
from functools import partial, wraps
from logging import getLogger
from re import sub
from sqlalchemy.orm import Query
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from time import time
from traceback import format_exc
from werkzeug.exceptions import HTTPException

logger = getLogger(__name__)

# Errors
# ======

class ConversionError(Exception):

  """Thrown when a row can't be parsed."""

  pass

class APIError(HTTPException):

  """Thrown when an API call is invalid.

  The error code will sent as error code for the response.

  """

  def __init__(self, code, message):
    self.code = code
    super(APIError, self).__init__(message)

  def __repr__(self):
    return '<APIError %r: %r>' % (self.code, self.message)

# Helpers
# =======

def prod(iterable, key=None, restrict=None):
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
    if not restrict or not restrict(elem):
      if key is None:
        rv *= elem
      else:
        rv *= key(elem)
  return rv

def uncamelcase(name):
  s1 = sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
  return sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def convert(value, return_type):
  """Converts a string to another builtin type."""
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
      raise ConversionError('Can\'t convert %s to boolean.' % value)
  elif return_type == 'unicode':
    return unicode(value, encoding='utf-8', errors='replace')
  elif return_type == 'str':
    return value
  # if we get here, something has gone wrong
  raise ConversionError('Invalid conversion type: %s' % return_type)

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

def histogram(
    data,
    key=lambda a: a,
    bins=50,
    restrict=None,
    categories=None,
    order=0,
    expand=False
):
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

# Classes
# -------

class SmartDictReader(DictReader):

  """Helper for importing .csv files.

  :param csvfile: open file instance
  :type csvfile: ``file``
  :param fields: sequence of tuples (fieldname, fieldtype)
  :rtype: generator

  Some csv files have unicode data which raises errors. This helper function
  automatically replaces non-ascii characters.

  Interesting values for kwargs can be:
  * delimiter = '\t'
  * quotechar = '\x07'

  """

  def __init__(self, csvfile, fields, silent=True, **kwargs):
    self.csvfile = csvfile
    self.n_imports = 0
    self.n_errors = 0
    self.silent = silent
    kwargs['fieldnames'] = [field[0] for field in fields]
    self.fieldtypes = dict(fields)
    DictReader.__init__(self, csvfile, **kwargs)

  def next(self):
    try:
      row = DictReader.next(self)
    except StopIteration:
      if self.n_errors:
        logger.warn('%s: %s rows imported, %s errors.' % (
            self.csvfile.name,
            self.n_imports,
            self.n_errors
        ))
      else:
        logger.info('%s: %s rows imported.' % (
            self.csvfile.name,
            self.n_imports
        ))
      raise StopIteration
    else:
      try:
        processed_row = dict(
            (key, convert(value, self.fieldtypes[key]))
            for key, value in row.iteritems()
            if self.fieldtypes[key]
        )
      except (ValueError, ConversionError) as e:
        logger.error(
            'Row processing error: %s. Full row: %s' % (e, row)
        )
        self.n_errors += 1
        if not self.silent:
          raise
      else:
        self.n_imports += 1
        return processed_row

# Caching
# ==========

class Cacheable(object):

  def get_cached_properties(self):
    return [
        varname
        for varname in dir(self.__class__)
        if isinstance(getattr(self.__class__, varname), CachedProperty)
    ]

  def refresh_cache(self):
    """Refresh all cached properties."""
    for varname in self.get_cached_properties():
      setattr(self, varname, True)

def cached_property(func):
  """Faster than smart_property."""
  return CachedProperty(func)

class CachedProperty(property):

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
        return {}
      return obj._cache[self.func.__name__][0]

  def __set__(self, obj, value):
    """Sets the value in the cache."""
    if not obj._cache: obj._cache = {}
    if value:
      obj._cache[self.func.__name__] = (self.func(obj), time())
      obj._cache.changed()

  def __repr__(self):
    return '<CachedProperty %s>' % self.func.__name__

def lazy_property(func):
  return LazyProperty(func)

class LazyProperty(property):

  """To distinguish certain properties.

  This is to emulate lazy loading. If we are at depth 0, we do not want
  to compute these properties.

  """

  pass

# Smart properties
# ----------------

def smart_property(cache=True, cache_category='', cache_history=False, jsonify=True):
  """A bit slow for now.

  @smart_property(cache=True)
  def foo(self, ...):
    ...

  * cache = False: no caching
  * cache = True: caching on a private variable
  * cache = 'some_string': caching on 'some_string' property

  The last one supports assignment as well (it wouldn't make sense for
  the second one to).

  * jsonify = True: always jsonified
  * jsonify = False: never jsonified
  * jsonify = 3: only jsonified if object jsonified at depth 3 or more

  """
  def wrapper(func):
    if cache == False:
      return SmartProperty(func, jsonify)
    if cache == True:
      return SmartLazyProperty(func, jsonify)
    elif cache and isinstance(cache, str):
      return SmartCachedProperty(func, cache, cache_category, jsonify)
  return wrapper

class SmartProperty(property):

  def __init__(self, func, jsonify):
    self.func = func
    self.__doc__ = func.__doc__
    self.min_depth = jsonify
    self.cache = None

  def __repr__(self):
    return '<SmartProperty %s>' % self.func.__name__

class SmartLazyProperty(SmartProperty):

  def __get__(self, obj, objtype=None):
    """Gets the value from cache (creating and refreshing as necessary)."""
    if obj is None:
      return self
    else:
      if self.cache is None:
        self.__set__(obj, self.func(obj))
      return self.cache

  def __set__(self, obj, value):
    if value:
      self.cache = value

  def __repr__(self):
    return '<LazyProperty %s>' % self.func.__name__

class SmartCachedProperty(SmartProperty):

  def __init__(self, func, jsonify, cache=None, cache_category=''):
    super(SmartCachedProperty, self).__init__(func, jsonify)
    self.cache = cache
    self.cache_cateogry = cache_category

  def __get__(self, obj, objtype=None):
    """Gets the value from cache (creating and refreshing as necessary)."""
    if obj is None:
      return self
    else:
      try:
        getattr(obj, self.cache)[self.func.__name__][0]
      except (AttributeError, TypeError):
        self.__set__(obj, self.func(obj))

  def __set__(self, obj, value):
    """Sets the value in the cache."""
    if not hasattr(obj, self.cache):
      setattr(obj, self.cache, {})
    if value:
      obj._cache[self.func.__name__] = (self.func(obj), time())
      # this should automatically be detected by the mutable if the
      # cache is an instance of a mutation dict
      # obj._cache.changed()

  def __repr__(self):
    return '<CachedProperty %s>' % self.func.__name__

# Jsonifification
# ===============

class Jsonifiable(object):

  """For easy API calls.

  We keep track of what has already been jsonified. There might still be
  some repetition given that we do not control the order of exploration.
  If a key is revisited at a lower depth, it will be reparsed to allow for
  more exploration.

  """

  _json_depth = -1
  _json_cost = {}
  _json_lazy = {}

  def get_id(self):
    if hasattr(self, 'id'):
      return {'id': self.id}
    else:
      return dict(
          (varname[:-3], {'id': getattr(self, varname)})
          for varname in dir(self)
          if varname.endswith('_id') and not varname == 'get_id'
      )

  def jsonify(self, depth=0, simple=True, verbose=False, show_keys=False):
    """Returns all keys and properties of an instance in a dictionary.

    :param depth:
    :type depth: int
    :param simple: wrap the result in a `Dict` before returning it
    :type simple: bool
    :param verbose: include non jsonifiable attribute names
    :type verbose: bool
    :param show_keys: show keys of nested models when at depth 0
    :type show_keys: bool
    :rtype: Dict or dict

    Keys and properties marked as private will not be returned.
    Lazy properties will only be returned if ...

    """
    if depth <= self._json_depth:
      # this instance has already been jsonified at a greater or
      # equal depth, so we simply return its key
      return self.get_id()
    self._json_depth = depth
    if isinstance(self, dict):
      d = dict(self)
    else:
      d = {}
    cls = self.__class__
    varnames = [
        e for e in dir(cls)
        if not e.startswith('_')  # don't show private properties
        if not e == 'metadata'    # for when used with models
    ]
    varnames = filter(
        lambda e: e == 'id' or not e.endswith('id'),
        varnames
    )
    for varname in varnames:
      cls_value = getattr(cls, varname)
      if isinstance(cls_value, (property, InstrumentedAttribute)):
        if not depth < cls._json_lazy.get(varname, 0):
          try:
            value = getattr(self, varname)
          except AttributeError:
            message = (
                'Can\'t read attribute %s on %s.'
                'Traceback: %s' % (varname, self, format_exc())
            )
            raise Exception(message)
          if hasattr(value, 'jsonify'):
            new_depth = depth - cls._json_cost.get(varname, 1)
            if new_depth >= 0:
              d[varname] = value.jsonify(depth=new_depth)
          elif isinstance(
                value,
                (dict, float, int, long, str, unicode)
          ):
            d[varname] = value
          elif isinstance(value, datetime):
            d[varname] = str(value)
          elif isinstance(value, list):
            list_elements = []
            # we do a check on the first element for efficiency
            if value:
              if isinstance(
                  value[0],
                  (dict, float, int, long, str, unicode)
              ):
                for e in value:
                  list_elements.append(e)
              elif hasattr(value[0], 'jsonify'):
                new_depth = depth - cls._json_cost.get(varname, 1)
                if new_depth >= 0:
                  for e in value:
                    list_elements.append(e.jsonify(depth=new_depth))
                elif show_keys and value[0]._json_cost > 0:
                  for e in value:
                    list_elements.append(e.get_id())
            d[varname] = list_elements
          elif verbose:
            # for debugging mostly
            if not value:
              d[varname] = None
            else:
              d[varname] = str(type(value))
    return d if simple else Dict(d)

class Loggable(object):

  """To easily log stuff.

  This implements the main logging methods ('debug', 'info', 'warn', 'error')
  directly on the class instance. For example, this allows something like::

    instance.log('Some message.')

  """

  def _logger(self, message, loglevel):
    if not hasattr(self, 'logger'):
      self.logger = getLogger(self.__module__)
    action = getattr(self.logger, loglevel)
    return action('%s :: %s' % (self, message))

  def __getattr__(self, varname):
    if varname in ['debug', 'info', 'warn', 'error']:
      return partial(self._logger, loglevel=varname)
    else:
      raise AttributeError

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

# Flask utilities
# ---------------

def api_response(default_depth=0, default_limit=20, wrap=True):
  """Decorator for API calls.

  Creates the response around any jsonifiable object. Also times the
  processing time and catches HTTPExceptions.

  If wrap is True, this wraps the result of the wrapped call with extra
  info before jsonifying the query results.

  Else, this sends back the results (jsonified if available) of the returned
  object.

  """
  def _api_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      timer = time()
      processing_times = []
      try:
        result = func(*args, **kwargs)
      except HTTPException as e:
        logger.error(format_exc())
        return jsonify({
          'status': 'error',
          'request': {
            'base_url': request.base_url,
            'method': request.method,
            'values': request.values
          },
          'content': str(e)
        }), e.code
      else:
        offset = max(0, request.args.get('offset', 0, int))
        limit = max(0, request.args.get('limit', default_limit, int))
        depth = max(0, request.args.get('depth', default_depth, int))
        if wrap == True or (
          isinstance(wrap, dict) and wrap[request.method] == True
        ):
          loaded = request.args.get('loaded', '')
          if loaded:
            loaded = [int(e) for e in loaded.split(',')]
          else:
            loaded = []
          processing_times.append(('request', time() - timer))
          timer = time()
          if isinstance(result, Query):
            total_matches = result.count()
            processing_times.append(('query', time() - timer))
            timer = time()
            if loaded:
              instance = result.column_descriptions[0]['type']
              result = result.filter(~instance.id.in_(loaded))
            response_content = [
              e.jsonify(depth=depth)
              for e in result.offset(offset).limit(limit)
            ]
          else:
            total_matches = len(result)
            response_content = [
              e.jsonify(depth=depth)
              for e in result[offset:offset + limit]
              if not e.id in loaded
            ]
          processing_times.append(('jsonification', time() - timer))
          return jsonify({
            'status': 'success',
            'processing_time': processing_times,
            'matches': {
              'total': total_matches,
              'returned': len(response_content)
            },
            'request': {
              'base_url': request.base_url,
              'method': request.method,
              'values': request.values
            },
            'content': response_content
          }), 200
        else:
          if hasattr(result, 'jsonify'):
            return jsonify(result.jsonify(depth=depth)), 200
          elif isinstance(result, dict):
            return jsonify(result), 200
          else:
            return jsonify({'result': result}), 200
    return wrapper
  return _api_response

# In progress
# -----------

# def pagify(func):
#   """Adds pagination to views."""
#   @wraps(func)
#   def wrapper(*args, **kwargs):
#     if 'p' in request.args:
#       page = max(0, int(request.args['p']) - 1)
#     else:
#       page = 0
#     return func(*args, page=page, **kwargs)
#   return wrapper
