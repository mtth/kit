#!/usr/bin/env python

"""Nested dictionary helpers."""

from collections import Mapping
from copy import deepcopy


def depth(dct):
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
  return max(depth(value) for value in values) + 1 if values else 1

def width(dct):
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
  return sum(width(value) for value in values) + len(dct) - len(values)

def flatten(dct, sep='_', prefix=''):
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
      items.extend(flatten(value, sep, k).items())
    else:
      items.append((k, value))
  return dict(items)

def unflatten(dct, sep='_', cname='all'):
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

def update(a, b, copy=False):
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
      a[k] = update(a.get(k, {}), v)
    else:
      a[k] = b[k]
  return a

