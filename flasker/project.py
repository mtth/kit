#!/usr/bin/env python

"""Project module."""

from celery.signals import task_postrun
from ConfigParser import SafeConfigParser
from flask import abort
from os.path import abspath, dirname, join, sep, split, splitext
from re import match, sub
from sqlalchemy import create_engine  
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session, sessionmaker
from weakref import proxy
from werkzeug.local import LocalProxy

from .util import convert

class ProjectImportError(Exception):

  pass

class Project(object):

  """Project class.

  Global container for the Flask and Celery apps and SQLAlchemy database
  object.
  
  """

  __current__ = None

  config = {
    'PROJECT': {
      'NAME': '',
      'DOMAIN': '',
      'SUBDOMAIN': '',
      'MODULES': '',
      'APP_FOLDER': 'app',
      'APP_STATIC_FOLDER': 'static',
      'APP_TEMPLATE_FOLDER': 'templates',
      'COMMIT_ON_TEARDOWN': True,
    },
    'ENGINE': {
      'URL': 'sqlite://',
    },
    'APP': {
      'SECRET_KEY': 'a_default_unsafe_key',
    },
    'CELERY': {
      'BROKER_URL': 'redis://',
      'CELERY_RESULT_BACKEND': 'redis://',
      'CELERY_SEND_EVENTS': True
    },
  }

  def __init__(self, config_path):

    config = self._parse_config(config_path)
    for key in config:
      if key in self.config:
        self.config[key].update(config[key])
      else:
        self.config[key] = config[key]

    self.root_dir = dirname(abspath(config_path))
    self.domain = (
      self.config['PROJECT']['DOMAIN'] or
      sub(r'\W+', '_', self.config['PROJECT']['NAME'].lower())
    )
    self.subdomain = (
      self.config['PROJECT']['SUBDOMAIN'] or
      splitext(config_path)[0].replace(sep, '-')
    )

    assert Project.__current__ is None, 'More than one project.'
    Project.__current__ = proxy(self)

    self.app = None
    self.celery = None
    self.session = None
    self._engine = None
    self._extensions = []
    self._before_startup = []

  def __repr__(self):
    return '<Project %r, %r>' % (self.config['PROJECT']['NAME'], self.root_dir)

  def register_extension(self, extension, config_section=None):
    """Register an extension."""
    self._extensions.append((extension, config_section))

  def before_startup(self, func):
    """Decorator, hook to run a function right before project starts."""
    self._before_startup.append(func)

  def _make(self, app=False, celery=False):
    """Create all project components."""
    # core
    for mod in  ['app', 'celery']:
      __import__('flasker.core.%s' % mod)
    # project modules
    project_modules = self.config['PROJECT']['MODULES'].split(',') or []
    for mod in project_modules:
      __import__(mod.strip())
    # database
    self._setup_database_connection()
    # extensions
    for extension, config_section in self._extensions or []:
      if config_section:
        for k, v in self.config[config_section].items():
          extension.config[k] = v
      extension._before_register(self)
      self.app.register_blueprint(extension.blueprint)
      extension._after_register(self)
    # final hook
    for func in self._before_startup or []:
      func(self)

  def _setup_database_connection(self):
    engine_ops = dict((k.lower(), v) for k,v in self.config['ENGINE'].items())
    self._engine = create_engine(engine_ops.pop('url'), **engine_ops)
    self.session = scoped_session(sessionmaker(bind=self._engine))

  def _dismantle_database_connections(self):
    """Remove database connections.

    Has to be called after app request/job terminates or connections
    will leak.

    """
    try:
      if self.config['PROJECT']['COMMIT_ON_TEARDOWN']:
        self.session.commit()
    except InvalidRequestError as e:
      self.session.rollback()
      self.session.expunge_all()
    finally:
      self.session.remove()

  def _parse_config(self, config_path):
    """Read the configuration file and return values as a dictionary.

    Raises ProjectImportError if no configuration file can be read at the
    file path entered.

    """
    parser = SafeConfigParser()
    parser.optionxform = str    # setting options to case-sensitive
    try:
      with open(config_path) as f:
        parser.readfp(f)
    except IOError as e:
      raise ProjectImportError(
        'Unable to parse configuration file at %s.' % config_path
      )
    conf = dict(
      (s, dict((k, convert(v)) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )
    # some conf checking
    if not conf['PROJECT']['NAME']:
      raise ProjectImportError('Missing project name.')
    return conf

  @classmethod
  def _get_current_project(cls):
    """Hook for ``current_project`` proxy."""
    return Project.__current__

current_project = LocalProxy(lambda: Project._get_current_project())

