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


class KitError(Exception):

  """Generic error class."""

  pass


class Kit(object):

  """Kit class.

  :param path: path to the configuration file.
  :type path: str
  
  """

  path = None

  _flasks = {}
  _celeries = {}
  _sessions = {}

  __state = {}

  def __init__(self, path=None):
    self.__dict__ = self.__state
    if path:
      if self.path and path != self.path:
        raise KitError('Invalid path specified: %r' % path)
      elif not self.path:
        self.path = abspath(path)
        with open(path) as f:
          self.config = load(f)
        self.config.setdefault('flasks', [])
        self.config.setdefault('celeries', [])
        self.config.setdefault('sessions', [])
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
    return [
      e['name']
      for category in ['flasks', 'celeries', 'sessions']
      for e in self.config[category]
    ]

  def get_flasks(self, name):
    """Flask application getter."""
    if name is None:
      return [self.get_flasks(e['name']) for e in self.config['flasks']]

    else:
      print name
      if name not in self._flasks:
        conf = self._get_options('flasks', name)
        flask_app = Flask(name, **conf.get('kwargs', {}))
        flask_app.config.update(
          {k.upper(): v for k, v in conf.get('config', {}).items()}
        )
        self._flasks[name] = flask_app

      return self._flasks[name]

  def get_celeries(self, name):
    """Celery application getter."""
    if name is None:
      return [self.get_celeries(e['name']) for e in self.config['celeries']]

    else:
      if name not in self._celeries:
        conf = self._get_options('celeries', name)
        celery_app = Celery(name, **conf.get('kwargs', {}))
        celery_app.conf.update(
          {k.upper(): v for k, v in conf.get('config', {}).items()}
        )
        celery_app.periodic_task = periodic_task
        self._celeries[name] = celery_app

      return self._celeries[name]

  def get_sessions(self, name):
    """SQLAlchemy scoped sessionmaker getter."""
    if name is None:
      return [self.get_sessions(e['name']) for e in self.config['sessions']]

    else:
      if name not in self._sessions:
        conf = self._get_options('sessions', name)
        engine = create_engine(
          conf.get('url', 'sqlite://'), **conf.get('engine', {})
        )
        session = scoped_session(
          sessionmaker(bind=engine, **conf.get('kwargs', {}))
        )
        self._sessions[name] = (session, conf.get('commit', False))

      return self._sessions[name][0]

  def _get_options(self, category, name):
    options = filter(
      lambda e: e['name'] == name,
      self.config[category]
    )
    if len(options) == 1:
      return options[0]
    elif len(options) > 1:
      raise KitError('Duplicate %s name %r found.' % (category, name))
    else:
      raise KitError('Undefined %s name %r.' % (category, name))


def _remove_session(sender, *args, **kwargs):
  """Globally namespaced function for signals to work."""
  if hasattr(sender, 'app'):
    # sender is a celery task
    app = sender.app
  else:
    # sender is a flask application
    app = sender
  for session, commit in Kit()._sessions:
    try:
      if commit:
        session.commit()
    except InvalidRequestError:
      session.rollback()
    finally:
      session.remove()

# Session removal handlers
task_postrun.connect(_remove_session)
request_tearing_down.connect(_remove_session)
