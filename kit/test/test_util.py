#!/usr/bin/env python

from flask import Flask
from nose.tools import eq_, raises

from kit.util import *


def test_uncamelcase():
  eq_(uncamelcase('CalvinAndHobbes'), 'calvin_and_hobbes')


class Test_Cacheable(object):

  def setup(self):

    class Example(Cacheable):

      @Cacheable.cached_property
      def number(self):
        return 10

      @Cacheable.cached_property
      def another(self):
        return 48

    self.ex = Example()

  def test_set_cache(self):
    eq_(self.ex.number, 10)
    self.ex.number = 2
    eq_(self.ex.number, 2)
    self.ex.number = 10

  def test_del_cache(self):
    eq_(self.ex.get_cache_ages()['number'], None)
    eq_(self.ex.number, 10)
    del self.ex.number
    eq_(self.ex.get_cache_ages()['number'], None)

  def test_refresh_cache(self):
    self.ex.number = 3
    self.ex.refresh_cache(['another'])
    eq_(self.ex.number, 3)
    self.ex.refresh_cache()
    eq_(self.ex.number, 10)

  def test_refresh_cache_expiration(self):
    self.ex.number = 3
    self.ex.refresh_cache(expiration=100)
    eq_(self.ex.number, 3)
    self.ex.refresh_cache()
    eq_(self.ex.number, 10)

  @raises(AttributeError)
  def test_refresh_cache_error(self):
    self.ex.refresh_cache(['number2'])

  def test_get_cache_ages(self):
    self.ex.refresh_cache()
    eq_(set(self.ex.get_cache_ages().keys()), set(['number', 'another']))


def test_to_json():

  class Foo(Jsonifiable):
    def __init__(self, n, nested=0):
      self.n = n
      if nested > 0:
        self.d = {str(n): Foo(n + 1, nested - 1)}
        self.f = Foo(n + 1, nested - 1)
        self.l = [Foo(n + 1, nested - 1)]
        self._p = 33
  foo = Foo(0, 2)
  j = foo.to_json()
  eq_(j, {'n': 0, 'd': {'0': {}}, 'f': {}, 'l': [{}]})
  j['n'] = 1
  j['d'] = {'1': {}}
  eq_(foo.to_json(depth=2), {'n': 0, 'd': {'0': j}, 'f': j, 'l': [j]})
  Foo.__json__ = ['n']
  eq_(foo.to_json(depth=2), {'n': 0})


class Test_View(object):

  def setup(self):
    self.app = Flask('test_app')
    self.View = make_view(self.app)
    self.client = self.app.test_client()

    class MyView(self.View):

      rules = {
        '/index/': ['GET'],
        '/index/<page>': ['GET', 'PUT'],
      }

      def get(self, **kwargs):
        if not kwargs:
          return 'no page'
        else:
          page = kwargs['page']
          return 'get page %s' % (page, )

      def put(self, **kwargs):
        page = kwargs['page']
        return 'put page %s' % (page, )

    self.MyView = MyView

  @raises(ValueError)
  def test_unbound(self):

    class UnboundView(View):

      rules = {
        '/unbound/': ['GET']
      }

  def test_ok_basic(self):
    eq_(self.client.get('/index/').data, 'no page')
    eq_(self.client.get('/index/1').data, 'get page 1')
    eq_(self.client.put('/index/1').data, 'put page 1')

  def test_not_allowed_basic(self):
    eq_(self.client.post('/index/').status_code, 405) # method not allowed
    eq_(self.client.put('/index/').status_code, 405) # method not allowed

  def test_not_allowed(self):

    class OtherView(self.MyView):

      methods = ['GET']
      
      rules = {
        '/other/': ['GET'],
        '/other/<page>': ['GET', 'PUT'],
      }

    eq_(self.client.get('/other/').data, 'no page')
    eq_(self.client.put('/other/1').status_code, 405)

  def test_not_implemented(self):

    class AnotherView(self.View):
      
      rules = {
        '/another/': ['GET'],
      }

    eq_(self.client.get('/another/').status_code, 404) # page not found

  @raises(ValueError)
  def test_no_rules(self):

    class YetAnotherView(self.View):

      def get():
        return 'hi'

    YetAnotherView.register_view()

  @raises(ValueError)
  def test_invalid_method(self):

    class YouGuessedItView(self.View):

      rules = {
        '/guess/': ['GET', 'A_WRONG_METHOD']
      }

      def get():
        return 'hi'
