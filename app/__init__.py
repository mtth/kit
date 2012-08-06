#!/usr/bin/env python

"""App factory module."""

# Logger

import logging
import logging.config

logger = logging.getLogger(__name__)

# App level imports

import app.config as x
import app.controllers as c

# Import the blueprints

from app.auth import initialize_bp

# Import the main app instance

from app.views import app as the_app

# The app factory!
# ================

def make_app(debug=False):
    """App factory."""
    # App and logger configuration
    the_app.config.from_object(x.BaseConfig)
    if debug:
        the_app.config.from_object(x.DebugConfig)
        logging.config.dictConfig(x.DEBUG_LOGGER_CONFIG)
    else:
        logging.config.dictConfig(x.LOGGER_CONFIG)
    # Initializing the database
    c.Session.initialize_db(debug)
    # Hooking up the authentication blueprint
    initialize_bp(the_app, debug)
    return the_app
