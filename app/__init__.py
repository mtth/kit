#!/usr/bin/env python

"""App factory module."""

import logging

logger = logging.getLogger(__name__)
# Do the logging configuration

# App level imports

import app.config as x

# Import the main app instance

from app.views import app

# Import the blueprints

import app.auth.views as auth

# The app factory!
# ================

def make_app(debug=False):
    """App factory."""
    if debug:
        app.config.from_object(x.DebugConfig)
    else:
        app.config.from_object(x.BaseConfig)
    # Hooking up the authentication blueprint
    app.register_blueprint(auth.bp)
    auth.login_manager.setup_app(app)
    return app
