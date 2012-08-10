#!/usr/bin/env python

"""App factory module."""

# Logger

import logging
import logging.config

logger = logging.getLogger(__name__)

# App level imports

from app.config.flask import BaseConfig, DebugConfig
from app.config.logging import DEBUG_LOGGER_CONFIG, LOGGER_CONFIG

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
        logging.config.dictConfig(DEBUG_LOGGER_CONFIG)
        Session.debug = True
    else:
        logging.config.dictConfig(LOGGER_CONFIG)
    # Initializing the database
    Session.initialize_db()
    # Hooking up the authentication blueprint
    init_auth_bp(the_app, debug)
    init_jobs_bp(the_app, debug)
    return the_app
