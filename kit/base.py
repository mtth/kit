  #!/usr/bin/env python

"""Core module.

This module defines the :class:`kit.Kit` class which contains all the logic
between the Flask and Celery applications and the SQLAlchemy sessions.

For convenience, both these variables are also available directly in the
``kit`` namespace.

"""

from logging import getLogger, NullHandler, StreamHandler, DEBUG
from os import getenv
from os.path import abspath, basename, dirname, join
from sys import path as sys_path
from weakref import proxy

try:
  from yaml import load
  from sqlalchemy.exc import InvalidRequestError
  from celery import current_app
except ImportError:
  pass


class KitImportError(Exception):

  """Generic error raised when something goes wrong during import."""

  pass


class Kit(object):

  """Kit class.

  :param path: path to the configuration file.
  :type path: str
  
  """

  #: Default configuration
  default_conf = {
    'flask':                    {},
    'celery':                   {},
    'sqlalchemy':               {},
    'modules':                  [],
    'root':                     '.',
    'debug':                    False,
  }

  _flask = None
  _celery = None
  _session = None

  __stack = []

  def __init__(self, path=None, load_modules=False):

    if not path:
      try:
        self.__dict__ = self.__stack[-1].__dict__
      except IndexError:
        raise KitImportError('Kit instantiated without a ``path`` argument '
                             'but outside of imports.')

    else:
      self.path = abspath(path)

      with open(path) as f:
        self.config = load(f)

      for k, v in self.default_conf.items():
        self.config.setdefault(k, v)

      self.logger = getLogger(__name__)
      self.logger.handlers = []
      if self.config['debug']:
        self.logger.setLevel(DEBUG)
        self.logger.addHandler(StreamHandler())
      else:
        self.logger.addHandler(NullHandler())

    if load_modules:
      with self:
        for module_name in self.config['modules']:
          self.logger.debug('Importing %s...' % (module_name, ))
          __import__(module_name)

  def __enter__(self):
    self.__stack.append(self)
    sys_path.insert(0, abspath(join(dirname(self.path), self.config['root'])))

  def __exit__(self, exc_type, exc_value, traceback):
    self.__stack.pop()
    sys_path.remove(abspath(join(dirname(self.path), self.config['root'])))

  def __repr__(self):
    return '<Kit %r>' % (self.path, )

  @property
  def flask(self):
    """Flask application.

    Lazily initialized.

    """
    if self._flask is None:

      from flask import Flask
      from flask.signals import request_tearing_down

      conf = self.config['flask']

      flask_app = Flask(conf.get('name', 'app'), **conf.get('kwargs', {}))
      flask_app.config.update(
        {k.upper(): v for k, v in conf.get('config', {}).items()}
      )

      flask_app._kit = proxy(self)
      request_tearing_down.connect(_remove_session, flask_app)

      self._flask = flask_app
      self.logger.debug('Flask app loaded')

    return self._flask

  @property
  def celery(self):
    """Celery application.

    Lazily initialized.

    """
    if self._celery is None:

      from celery import Celery
      from celery.signals import task_postrun
      from celery.task import periodic_task

      conf = self.config['celery']

      celery_app = Celery(**conf.get('kwargs', {}))
      celery_app.conf.update(
        {k.upper(): v for k, v in conf.get('config', {}).items()}
      )

      celery_app.periodic_task = periodic_task

      celery_app._kit = proxy(self)
      task_postrun.connect(_remove_session)

      self._celery = celery_app
      self.logger.debug('Celery app loaded')

    return self._celery

  @property
  def session(self):
    """SQLAlchemy scoped sessionmaker.

    Lazily initialized.

    """
    if self._session is None:

      from sqlalchemy import create_engine  
      from sqlalchemy.orm import scoped_session, sessionmaker

      conf = self.config['sqlalchemy']

      engine = create_engine(
        conf.get('url', 'sqlite://'), **conf.get('engine', {})
      )
      session = scoped_session(
        sessionmaker(bind=engine, **conf.get('session', {}))
      )

      self._session = session
      self.logger.debug('Session loaded')

    return self._session

  def _remove_session(self, flask=False, celery=False):
    """Remove database connections."""
    if self._session is not None:
      try:
        flask = flask and self.config['flask'].get('autocommit', False)
        celery = celery and self.config['celery'].get('autocommit', False)
        if flask or celery:
          self.session.commit()
      except InvalidRequestError as e:
        self.session.rollback()
        self.logger.error('Error while committing session: %s' % (e, ))
        if self.config['debug']:
          raise e
      finally:
        self.session.remove()


def _remove_session(sender, *args, **kwargs):
  """Globally namespaced function for signals to work."""
  if hasattr(sender, 'app'):
    # sender is a celery task
    sender.app._kit._remove_session(celery=True)
  else:
    # sender is a flask application
    sender._kit._remove_session(flask=True)


