#!/usr/bin/env python

from tempfile import NamedTemporaryFile
from nose.tools import eq_, raises

from flasker.util.helpers import *
from flasker.util.mixins import *
from flasker.util.ndict import *


def test_convert_auto():
  examples = [
    ('1', 1), ('None', None), ('hi', 'hi'), ('true', True), ('False', False),
    ('1.432', 1.432), ('1e-3', 1e-3)
  ]
  for example in examples:
    yield check_convert, example, None, False

def test_convert_json():
  examples = [
    ('1', 1), ('None', None), ('hi', 'hi'), ('true', True), ('False', False),
    ('1.432', 1.432), ('1e-3', 1e-3), ('null', None), ('{"a": 2}', {'a': 2}),
  ]
  for example in examples:
    yield check_convert, example, None, True

def test_convert_manual():
  all_examples = {
    'int': [
      ('1', 1),
    ],
    'float': [
      ('2.3', 2.3),
    ],
    'bool': [
      ('True', True),
      ('1', True),
      ('false', False),
      ('0', False),
    ],
    'unicode': [
      ('hello', u'hello'),
    ],
    'str': [
      ('string', 'string'),
    ],
    'json': [
      ('null', None),
      ('{"a": 23}', {'a': 23}),
    ]
  }
  for rtype, examples in all_examples.items():
    for example in examples:
      yield check_convert, example, rtype, False

def check_convert(example, rtype, allow_json):
  eq_(convert(example[0], rtype=rtype, allow_json=allow_json), example[1])

def test_partition_list():
  col = range(103)
  for i, (q, p) in enumerate(partition(col, size=5)):
    eq_(p.offset, 5 * i)
    eq_(p.limit, 5)
    if i < 20:
      eq_(len(q), 5)
    else:
      eq_(len(q), 3)

def test_prod():
  eq_(prod(range(1, 5)), 2 * 3 * 4)

def test_uncamelcase():
  eq_(uncamelcase('CalvinAndHobbes'), 'calvin_and_hobbes')

def test_parse_config():
  f = NamedTemporaryFile()
  f.write('[SECTION_A]\n'
          'FIRST = 3\n'
          'SECOND = hi')
  f.seek(0)
  eq_(parse_config(f), {'SECTION_A': {'first': 3, 'second': 'hi'}})
  f.seek(0)
  eq_(
    parse_config(f, case_sensitive=True),
    {'SECTION_A': {'FIRST': 3, 'SECOND': 'hi'}}
  )
  f.seek(0)
  eq_(
    parse_config(f, default={'SECTION_A': {'third': 0.0}, 'C': {'O': 2}}),
    {'SECTION_A': {'first': 3, 'second': 'hi', 'third': 0.0}, 'C': {'O': 2}}
  )
  f.close()


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
    for example, d in zip(self.examples, [3,2]):
      eq_(depth(example['u']), d)
      eq_(depth(example['f']), 1)

  def test_width(self):
    for example, w in zip(self.examples, [4,2]):
      for v in example.values():
        eq_(width(v), w)
  
  def test_flatten(self):
    example = self.examples[0]
    eq_(flatten(example['u']), example['f'])

  def test_unflatten(self):
    for example in self.examples:
      eq_(unflatten(example['f']), example['u'])

  def test_update(self):
    a = {'a': 1, 'b': {'c': 0}}
    b = {'a': 2, 'b': {'d': 1}}
    c = update(a, b)
    eq_(c, {'a': 2, 'b': {'c': 0, 'd': 1}})
    eq_(a, c)
    eq_(b, {'a': 2, 'b': {'d': 1}})

  def test_update_with_copy(self):
    a = {'a': 1, 'b': {'c': 0}}
    b = {'a': 2, 'b': {'d': 1}}
    c = update(a, b, copy=True)
    eq_(a, {'a': 1, 'b': {'c': 0}})
    eq_(b, {'a': 2, 'b': {'d': 1}})
  

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

