#!/usr/bin/env python

from __future__ import absolute_import

from flask import Flask
from flask.ext.login import current_user

from .oauth import make
from ..project import current_project

cp = current_project

app = Flask(
  'flask',
  static_folder=cp.APP_STATIC_FOLDER,
  template_folder=cp.APP_TEMPLATE_FOLDER
)

app.config.update(cp.APP_CONFIG.generate(cp))

@app.context_processor
def inject():
  def static_url(request):
    return cp.STATIC_URL or request.url_root + cp.APP_STATIC_FOLDER
  def is_logged_in():
    try:
      rv = current_user.is_authenticated()
    except AttributeError as e:
      # this will happen if this function is called when no
      # OAuth credentials have been entered
      rv = False
    finally:
      return rv
  return {
    'project_name': cp.NAME,
    'static_url': static_url,
    'is_logged_in': is_logged_in
  }

if cp.use_oauth():
  auth = make(cp.OAUTH_GOOGLE_CLIENT)
  app.register_blueprint(auth['bp'])
  auth['login_manager'].setup_app(app)

cp.app = app
