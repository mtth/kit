#!/usr/bin/env python

"""Project module.

The ``Project`` class and ``current_project`` proxy are defined here.

"""

from ConfigParser import SafeConfigParser
from logging import getLogger
from os.path import abspath, dirname, join, sep, split, splitext
from re import match, sub
from weakref import proxy
from werkzeug.local import LocalProxy

from util import convert

logger = getLogger('project')

class ProjectImportError(Exception):

  """Generic project import error.
  
  This will be raised for missing or invalid configuration files.
  
  """

  pass

class Project(object):

  """Project class.

  Global container for the Flask and Celery apps and SQLAlchemy database
  object.
  
  """

  __current__ = None

  _managers = None

  config = {
    'PROJECT': {
      'NAME': '',
      'DOMAIN': '',
      'SUBDOMAIN': '',
      'MODULES': '',
      'DB_URL': 'sqlite://',
      'APP_FOLDER': 'app',
      'APP_STATIC_FOLDER': 'static',
      'APP_TEMPLATE_FOLDER': 'templates',
    },
    'APP': {
      'SECRET_KEY': 'a_default_unsafe_key',
    },
    'CELERY': {
      'BROKER_URL': 'redis://',
      'CELERY_RESULT_BACKEND': 'redis://',
      'CELERY_SEND_EVENTS': True
    }
  }

  def __init__(self, config_path):

    config = self.parse_config(config_path)
    for key in config:
      if key in self.config:
        self.config[key].update(config[key])
      else:
        self.config[key] = config[key]
    self.check_config()

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
    self.db = None

  def __repr__(self):
    return '<Project %r, %r>' % (self.config['PROJECT']['NAME'], self.root_dir)

  def parse_config(self, config_path):
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
    return dict(
      (s, dict((k, convert(v)) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )

  def check_config(self):
    """Make sure the configuration is valid.

    Any a priori configuration checks will go here.
    
    """
    conf = self.config
    # check that the project has a name
    if not conf['PROJECT']['NAME']:
      raise ProjectImportError('Missing project name.')

  def setup_logger(self):
    """Setup the project logger.
    
    TODO.
    
    """
    pass

  def make(self):
    """Create all project components.

    Note that the database connection isn't created here.
    
    """
    for mod in  ['app', 'database', 'celery']:
      __import__('flasker.core.%s' % mod)
    project_modules = self.config['PROJECT']['MODULES'].split(',') or []
    for mod in project_modules:
      __import__(mod.strip())
    for manager, config_section in self._managers or []:
      if config_section:
        for k, v in self.config[config_section].items():
          manager.config[k] = v
      manager._before_register(self)
      self.app.register_blueprint(manager.blueprint)
      manager._after_register(self)

  def register_manager(self, manager, config_section=None):
    """Register a manager."""
    self._managers = self._managers or []
    self._managers.append((manager, config_section))

  @classmethod
  def get_current_project(cls):
    """Hook for ``current_project`` proxy."""
    return Project.__current__

current_project = LocalProxy(lambda: Project.get_current_project())

