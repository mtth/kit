#!/usr/bin/env python

from celery import Celery
from flask import Flask
from itertools import repeat
from json import loads
from nose.tools import ok_, eq_, nottest, raises, timed
from os import chdir, pardir
from os.path import abspath, dirname, exists, join
from requests import ConnectionError, get
from sqlalchemy.orm.scoping import scoped_session
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep, time

from flasker.project import *


class Test_Project(object):

  def setup(self):
    self.cp = abspath(
      join(
        dirname(__file__),
        pardir,
        pardir,
        'examples',
        'basic',
        'default.cfg'
      )
    )
    if not exists(self.cp):
      raise Exception('Missing configuration file')

  def teardown(self):
    Project._Project__state = {}

  @staticmethod
  def check_thread(creator, opj):
    pj = creator()
    eq_(pj.__dict__, opj.__dict__)
    eq_(pj.flask, opj.flask)
    eq_(pj.celery, opj.celery)
    eq_(pj.session, opj.session)

  def test_config_path(self):
    pj = Project(self.cp)
    eq_(self.cp, pj.conf_path)

  @raises(ProjectImportError)
  def test_unique_project(self):
    pj = Project(self.cp)
    another = Project('some/other/path.cfg')

  @raises(ProjectImportError)
  def test_empty_config_path(self):
    pj = Project()

  def test_components(self):
    pj = Project(self.cp)
    eq_(pj._flask, None)
    eq_(pj._celery, None)
    eq_(pj._session, None)
    eq_(type(pj.flask), Flask)
    eq_(type(pj.celery), Celery)
    eq_(type(pj.session), scoped_session)

  def test_borg_pattern(self):
    pj = Project(self.cp)
    another = Project()
    eq_(another.__dict__, pj.__dict__)

  def test_proxy(self):
    pj = Project(self.cp)
    eq_(current_project.__dict__, pj.__dict__)

  def test_threaded_project(self):
    pj = Project(self.cp)
    th = Thread(target=self.check_thread, args=(lambda: Project(), pj))
    th.start()
    th.join()

  def test_threaded_proxy(self):
    pj = Project(self.cp)
    th = Thread(target=self.check_thread, args=(lambda: current_project, pj))
    th.start()
    th.join()

  def test_app_server(self):
    pj = Project(self.cp)
    client = pj.flask.test_client()
    eq_(client.get('/').data, 'Hello World!')


# class Test_ConsoleTool(object):
# 
#   def setup(self):
#     chdir(abspath(
#       join(
#         dirname(__file__),
#         pardir,
#         pardir,
#         'examples',
#         'basic'
#       )
#     ))
#     self.sps = []
# 
#   def teardown(self):
#     for sp in self.sps:
#       if sp.poll() is not None:
#         sp.terminate()
# 
#   def open_subprocess(self, command):
#     sp = Popen(command)
#     # self.sps.append(sp)
#     return sp
# 
#   @timed(3)
#   def test_server(self):
#     sp = self.open_subprocess(['flasker', 'server', '-p', '5050'])
#     for _ in repeat(None, 4):
#       try:
#         sleep(1)
#         eq_(get('http://localhost:5050').json(), {'message': 'Welcome!'})
#         break
#       except ConnectionError:
#         pass
#     sp.terminate()
    
