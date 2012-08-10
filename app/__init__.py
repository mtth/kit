#!/usr/bin/env python

"""App factory module."""

# Logger

import logging
import logging.config

logger = logging.getLogger(__name__)

# App level imports

import app.conf as x
from app.core.database import Session

# Import the blueprints

from app.auth import initialize_bp

# Import the main app instance

from app.views import app as the_app

# The app factory!
# ================

def make_app(debug=False):
    """App factory."""
    # App and logger configuration
    the_app.config.from_object(x.flask.BaseConfig)
    if debug:
        the_app.config.from_object(x.flask.DebugConfig)
        # logging.config.dictConfig(x.LOGGER_CONFIG)
        Session.debug = True
    else:
        pass
    # Initializing the database
    Session.initialize_db()
    # Hooking up the authentication blueprint
    initialize_bp(the_app, debug)
    return the_app
