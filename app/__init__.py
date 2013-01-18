#!/usr/bin/env python

"""App factory module."""

from logging import getLogger
from logging.config import dictConfig

from app.core import initialize_bp as init_core_bp
from app.core.celery import celery
from app.core.config import CeleryBaseConfig, CeleryDebugConfig, \
BaseConfig, DebugConfig, DEBUG_LOGGER_CONFIG, LOGGER_CONFIG, STATIC_SERVER_URL
from app.core.database import Db
from app.views import app as the_app

logger = getLogger(__name__)

# The app factory!
# ================

@the_app.context_processor
def inject():
  def static_url(request):
    return STATIC_SERVER_URL or request.url_root + 'static/assets'
  return {
    'static_url': static_url
  }

def make_app(debug=False):
  """App factory."""
  # App and logger configuration
  the_app.config.from_object(BaseConfig)
  if debug:
    dictConfig(DEBUG_LOGGER_CONFIG)
    the_app.config.from_object(DebugConfig)
    celery.config_from_object(CeleryDebugConfig)
    Db.debug = True
  else:
    dictConfig(LOGGER_CONFIG)
    celery.config_from_object(CeleryBaseConfig)
  # Initializing the database
  Db.initialize(the_app)
  # Hooking up the blueprint
  init_core_bp(the_app, debug)
  return the_app
