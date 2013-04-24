#!/usr/bin/env python

"""Kit class module."""


from celery import Celery
from celery.signals import task_postrun
from celery.task import periodic_task
from collections import defaultdict
from flask import Flask
from flask.signals import request_tearing_down
from os.path import abspath, basename, dirname, join
from sqlalchemy import create_engine  
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session, sessionmaker
from sys import path as sys_path
from yaml import load


class Kit(object):

  """Kit class.

  :param path: path to the configuration file.
  :type path: str
  
  """

  path = None

  flask_apps = {}
  celery_apps = {}
  sessions = {}

  _session_bindings = {
    'flask': defaultdict(list),
    'celery': defaultdict(list),
  }

  __state = {}

  def __init__(self, path=None):
    self.__dict__ = self.__state
    if path:
      if self.path and path != self.path:
        raise Exception('wrong path: %s' % path)
      elif not self.path:
        self.path = abspath(path)
        with open(path) as f:
          self.config = load(f)
        self.config.setdefault('flask', {})
        self.config.setdefault('celery', {})
        if self.root not in sys_path:
          sys_path.insert(0, self.root)
        for module in self.modules:
          __import__(module)

  def __repr__(self):
    return '<Kit %r>' % (self.path, )

  @property
  def root(self):
    """Kit root path."""
    return abspath(join(dirname(self.path), self.config.get('root', '.')))

  @property
  def modules(self):
    """Modules to import."""
    return self.config['flask'].keys() + self.config['celery'].keys()

  def get_flask_app(self, name):
    """Flask application getter."""
    if name not in self.flask_apps:
      conf = self.config['flask'][name]
      flask_app = Flask(name, **conf.get('kwargs', {}))
      flask_app.config.update(
        {k.upper(): v for k, v in conf.get('config', {}).items()}
      )
      self.flask_apps[name] = flask_app
      for session_name in conf.get('bindings', []):
        self.add_binding(self.get_session(session_name), flask_app)
    return self.flask_apps[name]

  def get_celery_app(self, name):
    """Celery application getter."""
    if name not in self.celery_apps:
      conf = self.config['celery'][name]
      celery_app = Celery(name, **conf.get('kwargs', {}))
      celery_app.conf.update(
        {k.upper(): v for k, v in conf.get('config', {}).items()}
      )
      celery_app.periodic_task = periodic_task
      self.celery_apps[name] = celery_app
      for session_name in conf.get('bindings', []):
        self.add_binding(self.get_session(session_name), celery_app)
    return self.celery_apps[name]

  def get_session(self, name):
    """SQLAlchemy scoped sessionmaker getter."""
    if name not in self.sessions:
      conf = self.config['sqlalchemy'][name]
      engine = create_engine(
        conf.get('url', 'sqlite://'), **conf.get('engine', {})
      )
      session = scoped_session(
        sessionmaker(bind=engine, **conf.get('session', {}))
      )
      self.sessions[name] = session
    return self.sessions[name]

  def get_bindings(self, app):
    """App / session bindings."""
    if isinstance(app, Celery):
      return self._session_bindings['celery'][app.main]
    else:
      return self._session_bindings['flask'][app.name]

  def add_binding(self, session, app):
    """App / session bindings."""
    if isinstance(app, Celery):
      bindings = self._session_bindings['celery'][app.main]
    else:
      bindings = self._session_bindings['flask'][app.name]
    bindings.append(session)


def _remove_session(sender, *args, **kwargs):
  """Globally namespaced function for signals to work."""
  if hasattr(sender, 'app'):
    # sender is a celery task
    app = sender.app
  else:
    # sender is a flask application
    app = sender
  kit = Kit()
  bindings = kit.get_bindings(app)
  for session in kit.sessions.values():
    try:
      if session in bindings:
        session.commit()
    except InvalidRequestError:
      session.rollback()
    finally:
      session.remove()

# Session removal handlers
task_postrun.connect(_remove_session)
request_tearing_down.connect(_remove_session)
