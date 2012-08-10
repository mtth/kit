#!/usr/bin/env python

"""Jobs management blueprint."""

import views as v

__all__ = ['controllers.py', 'views.py']

def initialize_bp(the_app, debug=False):
    """Initialize the blueprint."""
    the_app.register_blueprint(v.bp)
