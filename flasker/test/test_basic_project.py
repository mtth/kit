#!/usr/bin/env python

from celery import Celery
from flask import Flask
from nose.tools import eq_, nottest, raises
from os import pardir
from os.path import abspath, dirname, exists, join
from sqlalchemy.orm.scoping import scoped_session
from threading import Thread

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
    Project._current = None
    Project.config_path = None

  @staticmethod
  def check_thread(creator, opj, strict):
    pj = creator()
    if strict:
      eq_(pj, opj)
    else:
      eq_(pj.__dict__, opj.__dict__)
    eq_(pj.flask, opj.flask)
    eq_(pj.celery, opj.celery)
    eq_(pj.session, opj.session)

  def test_before_startup(self):
    pj = Project(self.cp, False)
    before_startup = []

    @pj.before_startup
    def before_startup_handler(project):
      before_startup.append(1)

    pj._make()
    eq_(len(before_startup), 1)

  def test_config_path(self):
    pj = Project(self.cp)
    eq_(self.cp, pj.config_path)

  def test_registered(self):
    pj = Project(self.cp)
    eq_(pj, Project._current)

  @raises(ProjectImportError)
  def test_unique_project(self):
    pj = Project(self.cp)
    another = Project('some/other/path.cfg')

  @raises(ProjectImportError)
  def test_unique_project(self):
    pj = Project()

  def test_components(self):
    pj = Project(self.cp)
    eq_(type(pj.flask), Flask)
    eq_(type(pj.celery), Celery)
    eq_(type(pj.session), scoped_session)

  def test_borg_pattern(self):
    pj = Project(self.cp)
    another = Project()
    eq_(another.__dict__, pj.__dict__)

  def test_proxy(self):
    pj = Project(self.cp)
    eq_(current_project, pj)

  def test_threaded_project(self):
    pj = Project(self.cp)
    th = Thread(target=self.check_thread, args=(lambda: Project(), pj, 0))
    th.start()
    th.join()

  def test_threaded_proxy(self):
    pj = Project(self.cp)
    th = Thread(target=self.check_thread, args=(lambda: current_project, pj, 1))
    th.start()
    th.join()

