#!/usr/bin/env python

from __future__ import absolute_import

from flask import Flask

from .oauth import make
from ..project import current_project

app = Flask(
  current_project.NAME,
  static_folder=current_project.APP_STATIC_FOLDER,
  template_folder=current_project.APP_TEMPLATE_FOLDER
)

app.config.update(current_project.APP_CONFIG.generate(current_project))

@app.context_processor
def inject():
  def static_url(request):
    return current_project.STATIC_URL or request.url_root + 'static/assets'
  def is_logged_in():
    return current_project.use_oauth() and current_user.is_authenticated()
  return {
    'project_name': current_project.NAME,
    'static_url': static_url,
    'is_logged_in': is_logged_in
  }

if current_project.use_oauth():
  auth = make(current_project.OAUTH_GOOGLE_CLIENT)
  app.register_blueprint(auth['bp'])
  auth['login_manager'].setup_app(app)

current_project.app = app
