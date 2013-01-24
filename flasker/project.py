#!/usr/bin/env python

from logging import getLogger
from logging.config import dictConfig
from os.path import abspath, dirname, join, split
from sys import modules
from weakref import proxy
from werkzeug.local import LocalProxy

from . import config

logger = getLogger()

class BaseProject(object):

  """Base project class.

  All folder paths indicated here are relative to the folder where the project
  class is defined.

  """

  __current__ = None

  NAME = None
  MODULES = None
  DB_URL = None
  LOGGING_FOLDER = 'logs'
  APP_STATIC_FOLDER = 'static'
  APP_TEMPLATE_FOLDER = 'templates'
  CELERY_SCHEDULE_FOLDER = 'celery'
  APP_CONFIG = config.AppConfig
  CELERY_CONFIG = config.CeleryConfig
  LOGGER_CONFIG = config.LoggerConfig
  STATIC_URL = None
  OAUTH_GOOGLE_CLIENT = None

  def __init__(self):

    # BaseProject must be subclassed to gain access to project directory
    if not self.NAME:
      raise Exception("Subclass necessary.")
    else:
      assert BaseProject.__current__ is None, 'More than one project.'
      BaseProject.__current__ = proxy(self)

    # Making all paths absolute
    root_dir = abspath(dirname(modules[self.__class__.__module__].__file__))
    self.root_dir = root_dir
    self.LOGGING_FOLDER = join(root_dir, self.LOGGING_FOLDER)
    self.APP_STATIC_FOLDER = join(root_dir, self.APP_STATIC_FOLDER)
    self.APP_TEMPLATE_FOLDER = join(root_dir, self.APP_TEMPLATE_FOLDER)
    self.CELERY_SCHEDULE_FOLDER = join(root_dir, self.CELERY_SCHEDULE_FOLDER)
    if self.DB_URL is None:
      self.DB_URL = 'sqlite:///%s' % join(root_dir, 'db', 'db.sqlite')

    # Currently, 3 components to a project
    self.app = None
    self.celery = None
    self.db = None

  def __repr__(self):
    return '<%s %r (%r)>' % (self.__class__.__name__, self.NAME, self.root_dir)

  def use_oauth(self):
    return bool(self.OAUTH_GOOGLE_CLIENT)

  def make(self, debug=False):
    self.debug = debug
    self.logger = logger
    dictConfig(self.LOGGER_CONFIG.generate(self))
    __import__('flasker.components.app')
    __import__('flasker.components.database')
    __import__('flasker.components.celery')
    if self.MODULES:
      map(
        __import__, 
        ['%s.%s' % (split(self.root_dir)[1], mod) for mod in self.MODULES]
      )
    return self.app

  @classmethod
  def get_current_project(cls):
    return BaseProject.__current__

current_project = LocalProxy(lambda: BaseProject.get_current_project())
