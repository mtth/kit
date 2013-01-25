#!/usr/bin/env python

from ConfigParser import SafeConfigParser
from logging import getLogger
from logging.config import dictConfig
from os.path import abspath, dirname, join, split
from re import match
from weakref import proxy
from werkzeug.local import LocalProxy

logger = getLogger()

class ProjectImportError(Exception):

  pass

class Project(object):

  """Project class."""

  __current__ = None

  def __init__(self, config_path):

    self.root_dir = dirname(abspath(config_path))
    self.config = self.parse_config(config_path)
    self.check_config()

    assert Project.__current__ is None, 'More than one project.'
    Project.__current__ = proxy(self)

    # Currently, 3 components to a project
    self.app = None
    self.celery = None
    self.db = None

  def __repr__(self):
    return '<Project %r, %r>' % (self.config['PROJECT']['NAME'], self.root_dir)

  def force_coerce(self, key, value):
    """Coerce a string to something else, smartly.
    
    Also makes folder paths absolute.

    """
    if key.lower().endswith('_folder'):
      v = abspath(value)
    else:
      if value.lower() == 'true':
        v = True
      elif value.lower() == 'false':
        v = False
      else:
        try:
          v = int(value)
        except ValueError:
          try:
            v = float(value)
          except ValueError:
            v = value
    return (key, v)

  def parse_config(self, config_path):
    parser = SafeConfigParser()
    parser.optionxform = str    # setting options to case-sensitive
    try:
      with open(config_path) as f:
        parser.readfp(f)
    except IOError as e:
      raise ProjectImportError(
        'No configuration file found at %s.' % config_path
      )
    return dict(
      (s, dict(self.force_coerce(k, v) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )

  def check_config(self):
    """Make sure the configuration is valid."""
    if not match('^[a-z_]+$', self.config['PROJECT']['SHORTNAME']):
      raise ProjectImportError(
        'Invalid project shortname (only lowercase and underscores allowed).'
      )

  def make(self):
    self.logger = logger
    # dictConfig(self.LOGGER_CONFIG.generate(self))
    components = ['app', 'database', 'celery']
    map(__import__, ('flasker.components.%s' % c for c in components))
    if self.config['PROJECT']['MODULES']:
      map(__import__, self.config['PROJECT']['MODULES'].split(','))

  @classmethod
  def get_current_project(cls):
    return Project.__current__

current_project = LocalProxy(lambda: Project.get_current_project())
