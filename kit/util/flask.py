#!/usr/bin/env python

"""Flask helpers."""

from __future__ import absolute_import

from flask import request
from flask.views import View as _View

from . import uncamelcase

class _ViewMeta(type):

  """To register classes with an app or blueprint on definition."""

  http_methods = ['get', 'post', 'put', 'delete']

  def __new__(mcs, name, bases, dct):
    view_class = super(_ViewMeta, mcs).__new__(mcs, name, bases, dct)

    if view_class.rules:

      if not view_class.__app__:
        raise ValueError('%s is not bound to an app' % (view_class, ))

      if view_class.endpoint is None:
        view_class.endpoint = uncamelcase(view_class.__name__)

      if view_class.methods is None:
        methods = set(key.upper() for key in dct if key in mcs.http_methods)
        view_class.methods = sorted(methods or [])
      
      view_class.register_view(view_class.__app__)

    return view_class


class View(_View):

  """Base view class.

  Not to be used directly, should be subclassed or called via the function
  :func:`make_view`.

  If bound to an app, will automatically register itself for the rules defined
  in the rules property.
  
  """

  __metaclass__ = _ViewMeta
  __app__ = None

  endpoint = None
  methods = None
  rules = None

  @classmethod
  def register_view(cls, app):
    """Attach view to app or blueprint."""
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
    
    Similar to the ``flask.views.MethodView`` implementation: GET requests
    are passed to :meth:`get`, POST to :meth:`post`, etc.
    
    """
    meth = getattr(self, request.method.lower(), None)
    if meth is None and request.method == 'HEAD':
      meth = getattr(self, 'get', None)
    return meth(**kwargs)


def make_view(app, view_class=View, view_name='View', **kwargs):
  """Return base view class bound to app.

  :param app: the app (or blueprint) to be bound to
  :type app: Flask app or blueprint
  :param view_class: base view class
  :type view_class: kit.util.View
  :rtype: kit.util.View

  Any keyword arguments will be added to the class' dictionary.

  """
  kwargs.update({'__app__': app})
  return type(view_name, (view_class, ), kwargs)


