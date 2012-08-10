#!/usr/bin/env python

import logging

logger = logging.getLogger(__name__)

# General imports

from flask import abort, Blueprint, flash, redirect, request, \
render_template, url_for

# Creating the Blueprint
# ======================

bp = Blueprint(
        'jobs',
        __name__,
        url_prefix='/jobs',
        template_folder='jobs'
)

@bp.route('/')
def index():
    """Job history page."""
    return render_template('jobs.html')
