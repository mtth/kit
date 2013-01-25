#!/usr/bin/env python

from ConfigParser import SafeConfigParser
from logging import getLogger
from logging.config import dictConfig
from os.path import abspath, dirname, join, split
from weakref import proxy
from werkzeug.local import LocalProxy

logger = getLogger()

class Project(object):

  """Base project class.

  All folder paths indicated here are relative to the folder where the project
  class is defined.

  """

  __current__ = None

  def __init__(self, config_path):

    self.root_dir = dirname(abspath(config_path))
    self.config = self.parse_config(config_path)

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
    if key.lower().endswith('folder'):
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
    parser.read(config_path)
    return dict(
      (s, dict(self.force_coerce(k, v) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )

  def use_oauth(self):
    return bool(self.config['PROJECT']['OAUTH_CLIENT'])

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
