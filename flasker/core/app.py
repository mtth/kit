#!/usr/bin/env python

"""Creating the Flask application."""

from __future__ import absolute_import

from flask import Flask
from os.path import join, sep

from ..project import current_project

pj = current_project
conf = pj.config['PROJECT']

app = Flask(
  conf['APP_FOLDER'].replace(sep, '.'),
  static_folder=conf['APP_STATIC_FOLDER'],
  template_folder=conf['APP_TEMPLATE_FOLDER'],
  instance_path=join(pj.root_dir, conf['APP_FOLDER']),
  instance_relative_config=True,
)
app.config.update(pj.config['APP'])

@app.context_processor
def inject():
  return {
    'project_name': conf['NAME'],
  }

@app.teardown_request
def teardown_request_handler(exception=None):
  pj._dismantle_database_connections()

pj.app = app
