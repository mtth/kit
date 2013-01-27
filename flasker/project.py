#!/usr/bin/env python

from ConfigParser import SafeConfigParser
from os.path import abspath, dirname, join, split, splitext
from re import match, sub
from weakref import proxy
from werkzeug.local import LocalProxy

from util import smart_coerce

class ProjectImportError(Exception):

  """Generic project import error.
  
  This will be raised for missing or invalid configuration files.
  
  """

  pass

class Project(object):

  """Project class.

  Some notes on the default configuration to go here.
  
  """

  __current__ = None

  config = {
    'PROJECT': {
      'NAME': '',
      'MODULES': '',
      'DB_URL': 'sqlite://',
      'APP_STATIC_FOLDER': 'app/static',
      'APP_TEMPLATE_FOLDER': 'app/templates',
      'OAUTH_CLIENT': '',
      'AUTHORIZED_EMAILS': '',
    },
    'APP': {
      'SECRET_KEY': '',
    },
    'CELERY': {
      'BROKER_URL': 'redis://',
      'CELERY_RESULT_BACKEND': 'redis://',
      'CELERY_SEND_EVENTS': True
    }
  }

  def __init__(self, config_path):
    config = self.parse_config(config_path)
    for key in self.config:
      self.config[key].update(config[key])
    self.check_config()
    self.root_dir = dirname(abspath(config_path))
    self.kind = splitext(split(config_path)[1])[0]
    self.sname = sub(r'\W+', '_', self.config['PROJECT']['NAME'].lower())
    # create current_project proxy
    assert Project.__current__ is None, 'More than one project.'
    Project.__current__ = proxy(self)
    # project components, 3 as of right now
    self.app = None
    self.celery = None
    self.db = None

  def __repr__(self):
    return '<Project %r, %r>' % (self.config['PROJECT']['NAME'], self.root_dir)

  def parse_config(self, config_path):
    """Read the configuration file and return values as a dictionary.

    Also makes all folder paths absolute (necessary because the app creation
    will be relative to the flasker module path otherwise).

    """
    parser = SafeConfigParser()
    parser.optionxform = str    # setting options to case-sensitive
    try:
      with open(config_path) as f:
        parser.readfp(f)
    except IOError as e:
      raise ProjectImportError(
        'No configuration file found at %s.' % config_path
      )
    rv = dict(
      (s, dict((k, smart_coerce(v)) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )
    for key in rv['PROJECT']:
      if key.endswith('_FOLDER'):
        rv['PROJECT'][key] = abspath(rv['PROJECT'][key])
    return rv

  def check_config(self):
    """Make sure the configuration is valid.

    Any a priori configuration checks will go here.
    
    """
    conf = self.config
    if not conf['NAME']:
      raise ProjectImportError('Missing project name.')

  def make(self):
    """Create all project components.

    Note that the database connection isn't created here.
    
    """
    components = ['app', 'database', 'celery']
    map(__import__, ('flasker.components.%s' % c for c in components))
    if self.config['PROJECT']['MODULES']:
      map(__import__, self.config['PROJECT']['MODULES'].split(','))

  @classmethod
  def get_current_project(cls):
    """Hook for ``current_project`` proxy."""
    return Project.__current__

current_project = LocalProxy(lambda: Project.get_current_project())

