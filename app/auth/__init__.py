#!/usr/bin/env python

__all__ = ['controllers.py', 'views.py']

# Blueprint level imports

import controllers as c
import views as v

# Initialize the blueprint

def initialize_bp(the_app, debug=False):
    """Initialize the blueprint."""
    the_app.register_blueprint(v.bp)
    v.login_manager.setup_app(the_app)
