#!/usr/bin/env python

from celery import Celery
from flask import Flask
from itertools import repeat
from nose import run
from nose.tools import ok_, eq_, nottest, raises, timed
from os import chdir, close, pardir, unlink
from os.path import abspath, dirname, exists, join
from requests import ConnectionError, get
from sqlalchemy.orm.scoping import scoped_session
from subprocess import Popen, PIPE
from tempfile import mkstemp
from threading import Thread
from time import sleep, time

from kit import get_kit
from kit.base import Kit, KitError


@raises(KitError)
def test_empty_kit_path():
  kit = get_kit()


class Test_FirstExample(object):

  def setup(self):
    self.kit = get_kit('../../examples/tracker/conf.yaml')
    self.client = self.kit.flasks[0].test_client()

  def teardown(self):
    Kit._Kit__state = {}

  def test_config_path(self):
    kit = get_kit()
    eq_(self.kit.__dict__, kit.__dict__)

  @raises(KitError)
  def test_missing_conf_file(self):
    get_kit('/another/missing/path.cfg')

  def test_get_flask_app(self):
    eq_(self.kit.get_flask_app('app'), self.kit.flasks[0])

  def test_flask_app_config(self):
    eq_(self.kit.flasks[0].config['DEBUG'], True)

  @raises(KitError)
  def test_get_flask_app_no_module(self):
    self.kit.get_flask_app('wrong.module')

  def test_view(self):
    eq_(self.client.get('/').status_code, 200)

  @raises(KitError)
  def test_get_session_wrong_name(self):
    self.kit.get_session('wrong_name')

  def test_session_commit(self):

    def get_views(data):
      return [int(s) for s in data.split() if s.isdigit()][0]

    first = get_views(self.client.get('/').data)
    second = get_views(self.client.get('/').data)

    eq_(first + 1, second)


class Test_SecondExample(object):

  def setup(self):
    self.kit = get_kit('../../examples/poller/conf.yaml')
    self.client = self.kit.flasks[0].test_client()

  def teardown(self):
    Kit._Kit__state = {}

#   @raises(KitError)
#   def test_get_celery_app_no_module(self):
#     self.kit.get_celery_app('wrong.module')

if __name__ == '__main__':
  run()
    
