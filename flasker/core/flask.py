#!/usr/bin/env python

"""Creating the Flask application."""

from __future__ import absolute_import

from flask import Flask
from os.path import join, sep


def make_flask_app(project):

  conf = {k: v for k, v in project.config['FLASK'].items()}
  root_folder = conf.pop('ROOT_FOLDER').replace(sep, '.')

  app = Flask(
    root_folder,
    static_folder=conf.pop('STATIC_FOLDER'),
    template_folder=conf.pop('TEMPLATE_FOLDER'),
    instance_path=join(project.config['PROJECT']['ROOT_DIR'], root_folder),
    instance_relative_config=True,
  )

  app.config.update(conf)

  @app.teardown_request
  def teardown_request_handler(exception=None):
    project._dismantle_database_connections()

  return app

