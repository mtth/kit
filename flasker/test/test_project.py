#!/usr/bin/env python

from celery import Celery
from flask import Flask
from nose.tools import eq_
from os import pardir
from os.path import abspath, dirname, exists, join
from sqlalchemy.orm.scoping import scoped_session
from threading import Thread

from flasker.project import current_project, Project


class Test_Project(object):

  def setup(self):
    config_path = abspath(
      join(dirname(__file__), pardir, pardir, 'example', 'default.cfg')
    )
    if not exists(config_path):
      raise Exception('Missing configuration file')

    self.pj = Project(config_path, False)
    self.set_on_startup = []

    @self.pj.before_startup
    def on_startup(project):
      self.set_on_startup.append(1)

    self.pj._make()

  def test_registered(self):
    eq_(self.pj._Project__registered, True)

  def test_components(self):
    eq_(type(self.pj.flask), Flask)
    eq_(type(self.pj.celery), Celery)
    eq_(type(self.pj.session), scoped_session)

  def test_borg_pattern(self):
    another = Project(self.pj.config_path)
    eq_(another.__dict__, self.pj.__dict__)

  def test_proxy(self):
    eq_(current_project, self.pj)

  def test_threaded_borg_pattern(self):
    main_project = self.pj
    path = self.pj.config_path
      
    class _Thread(Thread):
      def run(self):
        self.pj = Project(path)
        eq_(self.compare_dict(), True)
        eq_(self.compare_object(), False)

      def compare_dict(self):
        return self.pj.__dict__ == main_project.__dict__

      def compare_object(self):
        return self.pj == main_project

    th = _Thread()
    th.start()
    th.join()

  def test_threaded_proxy(self):
    main_project = self.pj
    path = self.pj.config_path
    
    class _Thread(Thread):
      def run(self):
        eq_(self.compare_dict(), True)
        eq_(self.compare_object(), False)

      def compare_dict(self):
        return current_project.__dict__ == main_project.__dict__

      def compare_object(self):
        return current_project == main_project

    th = _Thread()
    th.start()
    th.join()

  def test_before_startup(self):
    eq_(len(self.set_on_startup), 1)

