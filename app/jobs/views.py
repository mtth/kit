#!/usr/bin/env python

import logging
logger = logging.getLogger(__name__)

# General imports

from flask import abort, Blueprint, flash, redirect, request, \
render_template, url_for
from flask.ext.login import login_required

# Blueprint imports

import models as m

# Creating the Blueprint
# ======================

bp = Blueprint(
        'jobs',
        __name__,
        url_prefix='/jobs',
)

@bp.route('/')
@login_required
def index():
    """Job history page."""
    logger.info('Visited job page!')
    jobs = m.Job.query.all()
    return render_template('jobs/index.html', jobs=jobs)
