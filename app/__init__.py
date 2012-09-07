#!/usr/bin/env python

"""App factory module."""

# Logger
from logging import getLogger
from logging.config import dictConfig

# App level imports
from app.config.celery import CeleryBaseConfig, CeleryDebugConfig
from app.config.flask import BaseConfig, DebugConfig
from app.config.logging import DEBUG_LOGGER_CONFIG, LOGGER_CONFIG
from app.ext.celery import celery
from app.ext.database import Db

# Import the blueprint
from app.core import initialize_bp as init_core_bp

# Import the main app instance
from app.views import app as the_app

logger = getLogger(__name__)

# The app factory!
# ================

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
