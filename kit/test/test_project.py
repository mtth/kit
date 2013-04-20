#!/usr/bin/env python

from celery import Celery
from flask import Flask
from itertools import repeat
from nose import run
from nose.tools import ok_, eq_, nottest, raises, timed
from os import chdir, close, pardir
from os.path import abspath, dirname, exists, join
from requests import ConnectionError, get
from sqlalchemy.orm.scoping import scoped_session
from subprocess import Popen, PIPE
from tempfile import mkstemp
from threading import Thread
from time import sleep, time

from kit.base import Kit, KitImportError


class Test_Project(object):

  def setup(self):
    self.handle, self.cp = mkstemp()
    with open(self.cp, 'w') as f:
      f.write('modules: []\ndebug: on')

  def teardown(self):
    close(self.handle)

  def make_basic_flask_client(self, kit):
    @kit.flask.route('/')
    def index():
      return 'Hello World!'
    return kit.flask.test_client()

  def test_session_removed(self):
    pj = Kit(self.cp)
    client = self.make_basic_flask_client(pj)
    session = pj.session
    client.get('/')

  def test_config_path(self):
    pj = Kit(self.cp)
    eq_(self.cp, pj.path)

  @raises(IOError)
  def test_missing_conf_file(self):
    pj = Kit(self.cp)
    another = Kit('/another/missing/path.cfg')

  @raises(KitImportError)
  def test_empty_config_path(self):
    pj = Kit()

  def test_components(self):
    pj = Kit(self.cp)
    eq_(pj._flask, None)
    eq_(pj._celery, None)
    eq_(pj._session, None)
    eq_(type(pj.flask), Flask)
    eq_(type(pj.celery), Celery)
    eq_(type(pj.session), scoped_session)

  def test_app_server(self):
    pj = Kit(self.cp)
    client = self.make_basic_flask_client(pj)
    eq_(client.get('/').data, 'Hello World!')

if __name__ == '__main__':
  run()
    
