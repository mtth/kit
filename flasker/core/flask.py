#!/usr/bin/env python

"""Creating the Flask application."""

from __future__ import absolute_import

from flask import Flask
from os.path import join, sep

from ..project import current_project
from ..util import make_view

pj = current_project
conf = pj.config['PROJECT']

app = Flask(
  conf['FLASK_ROOT_FOLDER'].replace(sep, '.'),
  static_folder=conf['FLASK_STATIC_FOLDER'],
  template_folder=conf['FLASK_TEMPLATE_FOLDER'],
  instance_path=join(pj.root_dir, conf['FLASK_ROOT_FOLDER']),
  instance_relative_config=True,
)
app.config.update(pj.config['FLASK'])

@app.context_processor
def inject():
  return {
    'project_name': conf['NAME'],
  }

@app.teardown_request
def teardown_request_handler(exception=None):
  pj._dismantle_database_connections()

app.View = make_view(app)

pj.flask = app
