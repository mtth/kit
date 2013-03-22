#!/usr/bin/env python

from celery import Celery
from flask import Flask
from nose.tools import eq_, nottest
from os import pardir
from os.path import abspath, dirname, exists, join
from sqlalchemy.orm.scoping import scoped_session
from threading import Thread

from flasker.project import current_project, Project, _local_storage


class Test_Project(object):

  def setup(self):
    self.cp = abspath(
      join(dirname(__file__), pardir, pardir, 'example', 'default.cfg')
    )
    if not exists(self.cp):
      raise Exception('Missing configuration file')

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
    eq_(pj, _local_storage._current_project)
    # eq_(self.pj.__dict__, _local_storage._current_project.__dict__)

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
    # eq_(current_project.__dict__, self.pj.__dict__)
    eq_(current_project, pj)

  # @nottest
  def test_threaded_borg_pattern(self):
    pj = Project(self.cp)
    cp = self.cp
      
    class _Thread(Thread):
      def run(self):
        self.pj = Project(cp)
        eq_(self.compare_dict(), True)
        eq_(self.compare_object(), False)

      def compare_dict(self):
        return self.pj.__dict__ == pj.__dict__

      def compare_object(self):
        return self.pj == pj

    th = _Thread()
    th.start()
    th.join()

  @nottest
  def test_threaded_proxy(self):
    pj = Project(self.cp)
    cp = self.cp
    
    class _Thread(Thread):
      def run(self):
        eq_(self.compare_dict(), True)
        eq_(self.compare_object(), False)

      def compare_dict(self):
        return current_project.__dict__ == pj.__dict__

      def compare_object(self):
        return current_project == pj

    th = _Thread()
    th.start()
    th.join()

  def teardown(self):
    _local_storage._current_project = None

