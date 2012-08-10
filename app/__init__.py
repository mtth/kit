#!/usr/bin/env python

"""App factory module."""

# Logger

from logging import getLogger
from logging.config import dictConfig

logger = getLogger(__name__)

# App level imports

from app.config.celery import celery_base, celery_debug
from app.config.flask import BaseConfig, DebugConfig
from app.config.logging import DEBUG_LOGGER_CONFIG, LOGGER_CONFIG

from app.core.celery import celery
from app.core.database import Session

# Import the blueprints

from app.auth import initialize_bp as init_auth_bp
from app.jobs import initialize_bp as init_jobs_bp

# Import the main app instance

from app.views import app as the_app

# The app factory!
# ================

def make_app(debug=False):
    """App factory."""
    # App and logger configuration
    the_app.config.from_object(BaseConfig)
    if debug:
        the_app.config.from_object(DebugConfig)
        dictConfig(DEBUG_LOGGER_CONFIG)
        celery.config_from_object(celery_debug)
        Session.debug = True
    else:
        dictConfig(LOGGER_CONFIG)
        celery.config_from_object(celery_base)
    # Initializing the database
    Session.initialize_db()
    # Hooking up the blueprint
    init_auth_bp(the_app, debug)
    init_jobs_bp(the_app, debug)
    return the_app
