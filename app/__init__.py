#!/usr/bin/env python

"""App factory module."""

import logging

logger = logging.getLogger(__name__)
# Do the logging configuration

# App level imports

import app.config as x
import app.views as v

# The app factory!
# ================

def make_app(debug=False):
    """App factory."""
    if debug:
        v.app.config.from_object(x.DebugConfig)
    else:
        v.app.config.from_object(x.BaseConfig)
    return v.app
