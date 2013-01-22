#!/usr/bin/env python

from celery import Celery
from flask import Flask
from flask.ext.login import current_user
from logging import getLogger
from logging.config import dictConfig
from os import listdir
from os.path import abspath, join

import config
import database
import manager
import oauth

logger = getLogger(__name__)

class Flasker(object):

  def __init__(self, project_name, **kwargs):
    """Project.
    
    Valid keyword arguments:

      * project_root
      * db_url
      * logging_folder
      * oauth_credentials
      * celery_folder
      * static_url
      * static_folder
      * template_folder

    """
    self.project_name = project_name
    self.project_root = abspath(kwargs.get('project_root', '.'))
    self.app = None
    self.celery = None
    self.db = database.Db(kwargs.get('db_url', 'sqlite://'))
    self.options = kwargs
    self.config = config.make(
      project_name=self.project_name,
      project_root=self.project_root,
      logging_folder=self.options.get('logging_folder', None),
      celery_folder=self.options.get('celery_folder', None)
    )
    dictConfig(self.config['logger'])

  def get_app(self):
    """The Flask application object."""
    if not self.app:
      self.app = Flask(
        __name__,
        static_folder=abspath(
          join(
            self.project_root,
            self.options.get('static_folder', 'static')
          )
        ),
        template_folder=abspath(
          join(
            self.project_root,
            self.options.get('template_folder', 'templates')
          )
        )
      )
      self.app.config.from_object(self.config['app'])
    return self.app

  def get_celery(self):
    """The Celery application object."""
    if not 'celery_folder' in self.options:
      raise Exception("""
        Celery requires a folder to store jobs schedules.
        Please specify a celery_folder.
      """)
    if not self.celery:
      self.celery_folder = abspath(
        join(self.project_root, kwargs['celery_folder'])
      )
      self.celery = Celery()
      self.celery.config_from_object(self.config['celery'])
    return self.celery

  def get_db(self):
    """The database hook."""
    return self.db

  def _make_app(self):
    use_oauth = 'oauth_credentials' in self.options
    if use_oauth:
      if 'db_url' not in self.options:
        raise Exception("""
          OAuth requires a database backend to keep track of authorized users.
          Please specify a db_url.
        """)
      auth = oauth.make(self.options['oauth_credentials'])
      self.app.register_blueprint(auth['bp'])
      auth['login_manager'].setup_app(self.app)
    @self.app.context_processor
    def inject():
      def static_url(request):
        return self.options.get('static_url', None) or request.url_root + 'static/assets'
      def is_logged_in():
        return use_oauth and current_user.is_authenticated()
      return {
        'project_name': self.project_name,
        'static_url': static_url,
        'is_logged_in': is_logged_in
      }

  def _make_celery(self, logger_config):
    celery.make(self.celery, self.db, logger_config)

  def make(self, debug=False):
    if self.app:
      self._make_app()
    else:
      raise Exception("""
        The app hasn't been instantiated yet.
        There needs to be at lease one call to get_app.
      """)
    if self.celery:
      self._make_celery(self.config['logger'])
    else:
      logger.debug('No call to celery detected. Skipping make.')
    return self.app

  def run(self):
    self.manager = manager.make(
      project_name=self.project_name,
      factory=self.make,
      db=self.db,
      use_oauth='oauth_credentials' in self.options,
      celery=self.celery
    )
    self.manager.run()

