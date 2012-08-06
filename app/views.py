#!/usr/bin/env python

# General imports

from flask import Flask, render_template

from functools import wraps

# App level imports

import app.models as m
import app.controllers as c
import app.tasks as t

# The Flask app!
# ==============

app = Flask(__name__)

# Helpers
# =======

def pagify(func):
    """Adds pagination to views."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'p' in request.args:
            page = max(0, int(request.args['p']) - 1)
        else:
            page = 0
        return func(*args, page=page, **kwargs)
    return wrapper

# View handlers
# =============

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jobs')
def jobs():
    return render_template('jobs.html')
