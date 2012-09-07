#!/usr/bin/env python

import logging

logger = logging.getLogger(__name__)

# General imports

from flask import abort, Blueprint, flash, redirect, request, \
render_template, url_for
from flask.ext.login import login_user, logout_user, \
current_user, login_required

from app.ext.database import Db
from app.ext.util import APIError

# Blueprint level imports

import controllers as c
import models as m

# Creating the Blueprint
# ======================

bp = Blueprint(
        'core',
        __name__
)

# Handlers
# ========

@bp.route('/sign_in')
def sign_in():
    """Sign in view.

    Generates the google login url (calling ``get_google_loging_url`` from the
    controller) and puts in in a nice picture to click on.

    """
    values = {'sign_in_url': c.get_google_login_url()}
    return render_template('core/sign_in.html', **values)

@bp.route('/oauth2callback')
def oauth2callback():
    """Handlers Google callback.

    Callbacks from the Google API first arrive here. However, since the token
    information is stored after the hash in the URL, Flask can't process it
    directly. Therefore this page renders a page with only JavaScript which
    then catches the token information and redirects to ``catch_token``.

    """
    logger.debug('Callback call from google. Tranferring to catch the token.')
    values = {'catch_token_url': url_for('.catch_token')}
    return render_template('scripts/get_token_from_hash.html', **values)

@bp.route('/catch_token')
def catch_token():
    """Catches the token and signs in the user if it passes validation.

    If the user got to the sign in page from an non anonymous authorized page
    he will be directly redirected there after sign in. Otherwise he will be
    redirected to the home page.

    """
    token = request.args['access_token']
    logger.debug('Successfully caught access token.')
    if not c.validate_token(token):
        flash("Invalid token.")
        logger.warn('Access token is invalid.')
        return redirect(url_for('.sign_in'))
    logger.debug('Access token is valid.')
    user_infos = c.get_user_info_from_token(token)
    logger.debug('Gathered user infos successfully.')
    user = m.User.query.filter(
            m.User.email == user_infos['email']
    ).first()
    if user:
        login_user(user)
        user.info('Signed in.')
        flash("You signed in successfully!", category='success')
    else:
        logger.warn('%s tried to sign in.' % user_infos['email'])
        flash("Sign in failed, I don't recognize you :(", category='error')
    return redirect(request.args['state'])
        
@bp.route('/sign_out')
def sign_out():
    """Sign out.

    Redirects to the home page after a successful sign out.

    """
    current_user.info('Signed out.')
    logout_user()
    flash("You signed out successfully!", category='success')
    return redirect(url_for('index'))

@bp.route('/jobs')
@login_required
def jobs():
    """Jobs."""
    logger.info('Visited job page!')
    jobs = m.Job.query.all()
    return render_template('core/index.html', jobs=jobs)

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
