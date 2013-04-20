#!/usr/bin/env python

from tempfile import NamedTemporaryFile
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

  def test_view_cache(self):
    self.ex.refresh_cache()
    eq_(set(self.ex.view_cache().keys()), set(['number', 'another']))


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

