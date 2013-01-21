#!/usr/bin/env python

"""The views, entry point to wonders."""

from flask import Flask, render_template
from logging import getLogger

logger = getLogger(__name__)

# The Flask app!
# ==============

app = Flask(__name__)

# View handlers
# =============

@app.route('/')
def index():
  """Splash page."""
  return render_template('index.html')

