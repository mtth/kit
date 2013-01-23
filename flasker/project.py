#!/usr/bin/env python

from __future__ import absolute_import

from celery import Celery
from celery.signals import worker_process_init, after_setup_logger
from celery.task import periodic_task
from flask import current_app, Flask
from flask.ext.login import current_user
from imp import load_source
from logging import getLogger
from logging.config import dictConfig
from os import listdir
from os.path import abspath, dirname, join, split, splitext
from sys import modules
from weakref import proxy
from werkzeug.local import LocalProxy

from . import config
from . import database
from . import oauth

logger = getLogger(__name__)

class BaseProject(object):

  """Base project class.

  All folder paths indicated here are relative to the current folder.

  """

  __current__ = None

  NAME = None
  DB_URL = 'sqlite://'
  LOGGING_FOLDER = 'logs'
  APP_STATIC_FOLDER = 'static'
  APP_TEMPLATE_FOLDER = 'templates'
  CELERY_SCHEDULE_FOLDER = 'celery'
  APP_CONFIG = config.AppConfig
  CELERY_CONFIG = config.CeleryConfig
  LOGGER_CONFIG = config.LoggerConfig
  MODULES = None
  STATIC_URL = None
  OAUTH_GOOGLE_CLIENT = None

  def __init__(self):
    # BaseProject must be subclassed to gain access to project directory
    if not self.NAME:
      raise Exception("Subclass necessary.")
    else:
      if BaseProject.__current__ is not None:
        raise Exception("More than one project initialized.")
      BaseProject.__current__ = proxy(self)

    # Making all paths absolute
    root_dir = abspath(dirname(modules[self.__class__.__module__].__file__))
    self.root_dir = root_dir
    self.LOGGING_FOLDER = join(root_dir, self.LOGGING_FOLDER)
    self.APP_STATIC_FOLDER = join(root_dir, self.APP_STATIC_FOLDER)
    self.APP_TEMPLATE_FOLDER = join(root_dir, self.APP_TEMPLATE_FOLDER)
    self.CELERY_SCHEDULE_FOLDER = join(root_dir, self.CELERY_SCHEDULE_FOLDER)

    # Currently, 3 elements to a project
    self.app = None
    self.celery = None
    self.db = None

  def __repr__(self):
    return '<BaseProject %r>' % self.NAME

  def use_oauth(self):
    return bool(self.OAUTH_GOOGLE_CLIENT)

  def _make_db(self, debug):
    self.db = database.Db(self.DB_URL)

  def _make_app(self, debug):
    """Configure and generate the Flask app."""
    self.app = Flask(
      self.NAME,
      static_folder=self.APP_STATIC_FOLDER,
      template_folder=self.APP_TEMPLATE_FOLDER
    )
    self.app.config.update(self.APP_CONFIG.generate(self, debug))

    if self.use_oauth():
      auth = oauth.make(self.OAUTH_GOOGLE_CLIENT)
      self.app.register_blueprint(auth['bp'])
      auth['login_manager'].setup_app(self.app)

    @self.app.context_processor
    def inject():

      def static_url(request):
        return self.STATIC_URL or request.url_root + 'static/assets'

      def is_logged_in():
        return self.use_oauth() and current_user.is_authenticated()

      return {
        'project_name': self.name,
        'static_url': static_url,
        'is_logged_in': is_logged_in
      }

  def _make_celery(self, debug):
    """Configure and generate the Celery app."""
    self.celery = Celery()
    self.celery.conf.update(self.CELERY_CONFIG.generate(self, debug))
    self.celery.periodic_task = periodic_task

    @after_setup_logger.connect
    def after_setup_logger_handler(logger, loglevel, logfile, **kwrds):
        """Setting up logger configuration for the worker."""
        self._make_logger(debug)

    def create_worker_connection(*args, **kwargs):
      """Initialize database connection.

      This has to be done after the worker processes have been started otherwise
      the connection will fail.

      """
      self.db.create_connection()

    worker_process_init.connect(create_worker_connection)

  def _make_logger(self, debug):
    dictConfig(self.LOGGER_CONFIG.generate(self, debug))

  def make(self, debug=False):
    print 'calling make app'
    self._make_db(debug)
    self._make_app(debug)
    self._make_celery(debug)
    self._make_logger(debug)
    print self.__class__.__module__
    if self.MODULES:
      project_modules = [
        '%s.py' % join(self.root_dir, module)
        for module in self.MODULES
      ]
    else:
      project_modules = []
    for module in project_modules:
      load_source(
        '%s.%s' % (split(dirname(module))[1], splitext(split(module)[1])[0]),
        module
      )
    return self.app

  @classmethod
  def get_current_project(cls):
    return BaseProject.__current__

current_project = LocalProxy(lambda: BaseProject.get_current_project())
