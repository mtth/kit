#!/usr/bin/env python

from celery import Celery
from flask import Flask
from itertools import repeat
from nose import run
from nose.tools import ok_, eq_, nottest, raises, timed
from os import chdir, close, pardir, unlink
from os.path import abspath, dirname, exists, join
from requests import ConnectionError, get
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.scoping import scoped_session
from subprocess import Popen, PIPE
from tempfile import mkstemp
from threading import Thread
from time import sleep, time

from kit import Celery, Flask, get_session, get_kit, teardown_handler
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
    flasks = self.kit.flasks
    eq_(len(flasks), 1)
    eq_(Flask('app'), flasks[0])

  def test_flask_app_config(self):
    eq_(self.kit.flasks[0].config['DEBUG'], True)

  @raises(KitError)
  def test_get_flask_app_no_module(self):
    Flask('wrong.module')

  def test_view(self):
    eq_(self.client.get('/').status_code, 200)

  def test_get_session(self):
    sessions = self.kit.sessions.values()
    eq_(len(sessions), 1)
    eq_(get_session('db'), sessions[0])

  @raises(KitError)
  def test_get_session_wrong_name(self):
    get_session('wrong_name')

  def test_no_celeries(self):
    eq_(len(self.kit.celeries), 0)

  def test_session_commit(self):

    def get_views(data):
      return [int(s) for s in data.split() if s.isdigit()][0]

    first = get_views(self.client.get('/').data)
    second = get_views(self.client.get('/').data)
    eq_(first + 1, second)

  def test_session_query(self):
    from app import Visit
    self.client.get('/') # make sure at least one visit
    session = get_session('db')
    visit = session.query(Visit).first()
    eq_(visit.id, 1)

  @raises(IntegrityError)
  def test_session_integrity(self):
    from app import Visit
    with self.kit.flasks[0].test_request_context('/'):
      session = get_session('db')
      visit = Visit(id=1)
      session.add(visit)

  def test_teardown_handler(self):
    from app import Visit

    @teardown_handler
    def handler(session, app, options):
      session.remove() # don't commit

    with self.kit.flasks[0].test_request_context('/'):
      session = get_session('db')
      visit = Visit(id=1)
      session.add(visit)

    del self.kit._teardown_handler

if __name__ == '__main__':
  run()
    
