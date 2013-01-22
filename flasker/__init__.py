#!/usr/bin/env python

from celery import Celery
from flask import Flask
from flask.ext.login import current_user
from logging import getLogger
from logging.config import dictConfig
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
    self.options = kwargs
    self.project_root = abspath(kwargs.get('project_root', 'app'))
    if 'logging_folder' in kwargs:
      self.logging_folder = abspath(
        join(self.project_root, kwargs['logging_folder'])
      )
    else:
      self.logging_folder = None
    self.app = Flask(
      __name__,
      static_folder=abspath(
        join(self.project_root, kwargs.get('static_folder', 'static'))
      ),
      template_folder=abspath(
        join(self.project_root, kwargs.get('template_folder', 'templates'))
      )
    )
    self.db = database.Db(kwargs.get('db_url', 'sqlite://'))
    if 'celery_folder' in kwargs:
      self.celery_folder = abspath(
        join(self.project_root, kwargs['celery_folder'])
      )
      self.celery = Celery()
    else:
      self.celery_folder = None
      self.celery = None

  def get_app(self):
    """Used to keep track of where the app was called to know which modules
    to import."""
    return self.app

  def get_celery(self):
    return self.celery

  def get_db(self):
    return self.db

  def _make_app(self, app_config, logger_config):
    self.app.config.from_object(app_config)
    use_oauth = 'oauth_credentials' in self.options
    if use_oauth:
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

  def _make_celery(self, celery_config, logger_config):
    celery.make(self.celery, self.db, logger_config)
    self.celery.config_from_object(celery_config)

  def make(self, debug=False):
    self.config = config.make(
      project_name=self.project_name,
      project_root=self.project_root,
      logging_folder=self.logging_folder,
      celery_folder=self.celery_folder,
      debug=debug
    )
    dictConfig(self.config['logger'])
    self._make_app(self.config['app'], self.config['logger'])
    if self.celery:
      self._make_celery(self.config['celery'], self.config['logger'])
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

