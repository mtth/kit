#!/usr/bin/env python

import logging
logger = logging.getLogger(__name__)

# General imports
from flask import abort, Blueprint, flash, jsonify, make_response, redirect,\
request, render_template, url_for
from flask.ext.login import login_required

# App imports
from app.core.util import APIError

# Blueprint imports
import controllers as c
import models as m

# Creating the Blueprint
# ======================

bp = Blueprint(
        'jobs',
        __name__,
        url_prefix='/jobs',
)

@bp.route('/')
def index():
    """Job history page."""
    logger.info('Visited job page!')
    jobs = m.Job.query.all()
    return render_template('jobs/index.html', jobs=jobs)

@bp.route('/active')
@login_required
def active():
    """Active jobs."""
    logger.info('Visited job page!')
    jobs = m.Job.query.all()
    return render_template('jobs/index.html', jobs=jobs)

@bp.route('/lookup')
def lookup():
    """Information retrieval hook."""
    try:
        result = c.lookup(**request.args)
        status = 'Success!'
    except APIError as e:
        status = 'Invalid request: %s.' % e
        result = ''
    response = make_response(jsonify({
            'status': status,
            'query': request.args,
            'result': result
    }))
    # For external API calls
    response.headers['Access-Control-Allow-Origin'] = 'http://nncsts.com'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response
