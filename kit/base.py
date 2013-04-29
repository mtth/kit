#!/usr/bin/env python

"""Kit class module."""


from celery import Celery
from celery.signals import task_postrun
from celery.task import periodic_task
from flask import Flask
from flask.signals import request_tearing_down
from os.path import abspath, dirname, join
from sqlalchemy import create_engine  
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
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
  _sessions = {}

  __state = {}

  def __init__(self, path=None):
    self.__dict__ = self.__state
    if not path:
      if not self.path:
        raise KitError('No path specified')

    else:
      path = abspath(path)

      if self.path and path != self.path:
        raise KitError('Invalid path specified: %r' % path)

      elif not self.path:
        self.path = path

        with open(path) as handle:
          self.config = load(handle)

        if self.root not in sys_path:
          sys_path.insert(0, self.root)

        for module in self._modules:
          __import__(module)

        # Session removal handlers
        task_postrun.connect(_remove_session)
        request_tearing_down.connect(_remove_session)

  def __repr__(self):
    return '<Kit %r>' % (self.path, )

  @property
  def _modules(self):
    """Modules to import on kit load."""
    conf = self.config
    return conf.get('modules', []) + [
      module
      for app_conf in conf.get('flasks', []) + conf.get('celeries', [])
      for module in app_conf.get('modules', [])
    ]

  @property
  def root(self):
    """Kit root path."""
    return abspath(join(dirname(self.path), self.config.get('root', '.')))

  @property
  def sessions(self):
    """SQLAlchemy scoped sessionmaker getter."""
    return {k: v[0] for k, v in self._sessions.items()}

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

  def get_session(self, session_name):
    """SQLAlchemy session getter."""
    if session_name not in self._sessions:

      try:
        conf = self.config['sessions'][session_name]
      except KeyError:
        raise KitError('No session %r found' % (session_name, ))

      engine = create_engine(
        conf.get('url', 'sqlite://'), **conf.get('engine', {})
      )
      session = scoped_session(
        sessionmaker(bind=engine, **conf.get('kwargs', {}))
      )

      options = conf.get('options', {})
      options.setdefault('commit', False)
      options.setdefault('raise', True)

      self._sessions[session_name] = (session, options)
    return self._sessions[session_name][0]

  def _get_options(self, kind, module_name):
    """Options dictionary for the corresponding app."""
    configs = [
      config
      for config in self.config.get(kind, [])
      if module_name in config.get('modules', [])
    ]
    if len(configs) == 1:
      config = configs[0]
      def letters_generator(modules):
        for letters in map(set, zip(*modules)):
          if len(letters) == 1:
            yield letters.pop()
          else:
            return
      name = ''.join(letters_generator(config['modules'])).rstrip('.')
      return name, config
    elif len(configs) > 1:
      raise KitError('Duplicate %s for module %r found.' % (kind, module_name))
    else:
      raise KitError('Undefined %s for module  %r.' % (kind, module_name))
    
  def on_teardown(self, app, task=None):
    """Callback on request / task teardown.

    Default implementation calls the teardown handler on all the defined
    sessions.
    
    """
    for session, options in self._sessions.values():
      self._teardown_handler(session, app, options)

  @staticmethod
  def _teardown_handler(session, app, session_options):
    """Static method to allow overriding without passing first argument."""
    try:
      if session_options['commit']:
        session.commit()
    except (DBAPIError, SQLAlchemyError) as err:
      if session_options['raise']:
        raise err
      session.rollback()
    finally:
      session.remove()


def _remove_session(sender, *args, **kwargs):
  """Globally namespaced function for signals to work."""
  if hasattr(sender, 'app'):  # sender is a celery task
    app = sender.app
    task = sender
  else:                       # sender is a flask application
    app = sender
    task = None
  try:
    kit = Kit()
  except KitError:            # probably in nosetests
    pass
  else:
    kit.on_teardown(app, task)
