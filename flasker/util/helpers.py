#!/usr/bin/env python

"""General helpers."""

from __future__ import absolute_import

from collections import Mapping, namedtuple
from ConfigParser import SafeConfigParser
from copy import deepcopy
from csv import DictReader
from datetime import datetime
from decimal import Decimal
from json import loads
from re import sub
from sqlalchemy.orm import Query


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
    # nested dictionary update function
    def update(a, b):
      for k, v in b.iteritems():
        if isinstance(v, Mapping):
          a[k] = update(a.get(k, {}), v)
        else:
          a[k] = b[k]
      return a

    conf = update(deepcopy(default), conf)

  return conf

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

