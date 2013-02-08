#!/usr/bin/env python

"""Creating the Flask application."""

from __future__ import absolute_import

from flask import Flask

from ..project import current_project, Project

pj = current_project
conf = pj.config['PROJECT']

app = Flask(
  conf['APP_FOLDER'],
  static_folder=conf['APP_STATIC_FOLDER'],
  template_folder=conf['APP_TEMPLATE_FOLDER'],
  instance_path=pj.root_dir,
  instance_relative_config=True
)
app.config.update(pj.config['APP'])

@app.context_processor
def inject():
  def static_url(request):
    return conf['STATIC_URL'] or request.url_root + conf['APP_STATIC_FOLDER']
  return {
    'project_name': conf['NAME'],
    'static_url': static_url,
  }

pj.app = app