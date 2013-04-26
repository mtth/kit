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
  flasks = []
  celeries = []

  _registry = {'flasks': {}, 'celeries': {}}
  _sessions = []

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

        for module in self._modules:
          __import__(module)

  def __repr__(self):
    return '<Kit %r>' % (self.path, )

  @property
  def _modules(self):
    return [
      module
      for app_conf in self.config['flasks'] + self.config['celeries']
      for module in app_conf.get('modules', [])
    ]

  @property
  def root(self):
    """Kit root path."""
    return abspath(join(dirname(self.path), self.config.get('root', '.')))

  @property
  def sessions(self):
    """SQLAlchemy scoped sessionmaker getter."""
    if not self._sessions:
      for conf in self.config['sessions']:
        engine = create_engine(
          conf.get('url', 'sqlite://'), **conf.get('engine', {})
        )
        session = scoped_session(
          sessionmaker(bind=engine, **conf.get('kwargs', {}))
        )
        self._sessions.append((session, conf.get('commit', True)))
    return list(zip(*self._sessions)[0])

  def get_flask_app(self, module_name):
    """Application getter."""
    if module_name not in self._registry['flasks']:
      name, conf = self._get_options('flasks', module_name)
      flask_app = Flask(name, **conf.get('kwargs', {}))
      flask_app.config.update(
        {k.upper(): v for k, v in conf.get('config', {}).items()}
      )
      self.flasks.append(flask_app)
      for module in conf['modules']:
        self._registry['flasks'][module] = flask_app
    return self._registry['flasks'][module_name]

  def get_celery_app(self, module_name):
    """Celery application getter."""
    if module_name not in self._registry['celeries']:
      name, conf = self._get_options('celeries', module_name)
      celery_app = Celery(name, **conf.get('kwargs', {}))
      celery_app.conf.update(
        {k.upper(): v for k, v in conf.get('config', {}).items()}
      )
      celery_app.periodic_task = periodic_task
      self.celeries.append(celery_app)
      for module in conf['modules']:
        self._registry['celeries'][module] = celery_app
    return self._registry['celeries'][module_name]

  def _get_options(self, kind, module_name):
    configs = filter(
      lambda e: module_name in e.get('modules', []),
      self.config[kind]
    )
    if len(configs) == 1:
      config = configs[0]
      def letters_generator():
        for letters in map(set, zip(*config['modules'])):
          if len(letters) == 1:
            yield letters.pop()
          else:
            return
      name = ''.join(letters_generator())
      return name, config
    elif len(configs) > 1:
      raise KitError('Duplicate %s name %r found.' % (kind, name))
    else:
      raise KitError('Undefined %s name %r.' % (kind, name))

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
