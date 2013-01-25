#!/usr/bin/env python

from __future__ import absolute_import

from flask import Flask
from flask.ext.login import current_user

from ..project import current_project, Project
from .oauth import make

pj = current_project
conf = pj.config['PROJECT']

app = Flask(
  'flask',
  static_folder=conf['APP_STATIC_FOLDER'],
  template_folder=conf['APP_TEMPLATE_FOLDER']
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

auth = make(conf['OAUTH_CLIENT'])
app.register_blueprint(auth['bp'])
auth['login_manager'].setup_app(app)

pj.app = app
