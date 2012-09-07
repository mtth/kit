#!/usr/bin/env python

"""The views, entry point to wonders."""

# Logger
import logging
logger = logging.getLogger(__name__)

# General imports
from flask import flash, Flask, redirect, render_template, url_for

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
    logger.debug('Visited front page!')
    return render_template('index.html')

@app.route('/test')
def test():
    """Example of calling a Celery task."""
    logger.debug('Visited test page.')
    t.do_something.delay()
    return redirect(url_for('index'))
