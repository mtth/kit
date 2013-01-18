#!/usr/bin/env python

from app.core.auth import bp, login_manager

# Initialize the blueprint

def initialize_bp(the_app, debug=False):
    """Initialize the blueprint."""
    the_app.register_blueprint(bp)
    login_manager.setup_app(the_app)
