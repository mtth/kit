#!/usr/bin/env python

from nose.tools import eq_, raises

from flasker.util import *


def test_prod():
  eq_(prod(range(1, 5)), 2 * 3 * 4)

def test_uncamelcase():
  eq_(uncamelcase('CalvinAndHobbes'), 'calvin_and_hobbes')


class Test_Dict(object):

  def setup(self):
    self.examples = [
      {
        'u': {
          'a': 1,
          'b': {
            'c': None,
            'd': 'Cat',
          },
          'c': {
            '1': {
              'A': []
            }
          },
        },
        'f': {
          'a': 1,
          'b_c': None,
          'b_d': 'Cat',
          'c_1_A': [],
        }
      },
      {
        'u': {
          'd': {
            'all': 0,
            'e': -1,
          },
        },
        'f': {
          'd': 0,
          'd_e': -1,
        }
      }
    ]

  def test_depth(self):
    for example, depth in zip(self.examples, [3,2]):
      eq_(Dict.depth(example['u']), depth)
      eq_(Dict.depth(example['f']), 1)

  def test_width(self):
    for example, width in zip(self.examples, [4,2]):
      for v in example.values():
        eq_(Dict.width(v), width)
  
  def test_flatten(self):
    example = self.examples[0]
    eq_(Dict.flatten(example['u']), example['f'])

  def test_unflatten(self):
    for example in self.examples:
      eq_(Dict.unflatten(example['f']), example['u'])
  

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

  @raises(AttributeError)
  def test_refresh_cache_error(self):
    self.ex.refresh_cache(['number2'])

  def test_view_cache(self):
    self.ex.refresh_cache()
    eq_(set(self.ex.view_cache().keys()), set(['number', 'another']))


def test_to_json():
  # TODO
  pass

