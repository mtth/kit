#!/usr/bin/env python

"""Creating the Flask application."""

from __future__ import absolute_import

from flask import Flask
from os.path import join, sep

from ..project import current_project as pj, Project

conf = pj.config['FLASK']
root_folder = conf.pop('ROOT_FOLDER').replace(sep, '.')

app = Flask(
  root_folder,
  static_folder=conf.pop('STATIC_FOLDER'),
  template_folder=conf.pop('TEMPLATE_FOLDER'),
  instance_path=join(pj.root_dir, root_folder),
  instance_relative_config=True,
)

app.config.update(conf)

@app.teardown_request
def teardown_request_handler(exception=None):
  pj._dismantle_database_connections()

Project.flask = app

