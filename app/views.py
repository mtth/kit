#!/usr/bin/env python

"""The views, entry point to wonders."""

# Logger

import logging

logger = logging.getLogger(__name__)

# General imports

from flask import flash, Flask, render_template

# App level imports

import app.models as m
import app.controllers as c
import app.tasks as t

# The Flask app!
# ==============

app = Flask(__name__)

# View handlers
# =============

@app.route('/')
def index():
    """Splash page."""
    logger.info('Visited front page!')
    return render_template('index.html')
