#!/usr/bin/env python

import logging

logger = logging.getLogger(__name__)

# General imports

from flask import abort, Blueprint, flash, redirect, request, \
render_template, url_for

from flask.ext.login import LoginManager, login_user, logout_user, \
current_user, login_required

# App level imports

# Blueprint level imports

import controllers as c

# Creating the Blueprint
# ======================

bp = Blueprint('auth', __name__, url_prefix='')

# Module configuration
# ====================

login_manager = LoginManager()

login_manager.login_view = '/sign_in'
login_manager.login_message = ("a little bird tells me you have to sign in"
                               " before coming here")

@login_manager.user_loader
def load_user(user_email):
    """Return the user from his email.

    :param user_email: user email
    :type user_email: unicode
    :rtype: User

    Necessary for flask.login module.
    
    """
    return c.User(user_email)

# Handlers
# ========

@bp.route('/sign_in')
def sign_in():
    """Sign in view.

    Generates the google login url (calling ``get_google_loging_url`` from the
    controller) and puts in in a nice picture to click on.

    """
    values = {'sign_in_url': c.get_google_login_url()}
    return render_template('sign_in.html', **values)

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
    user = c.User(user_infos['email'])
    if user:
        login_user(user)
        logger.info('%s signed in.' % current_user.email)
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
    logger.info('%s signed out.' % current_user.email)
    logout_user()
    flash("You signed out successfully!", category='success')
    return redirect(url_for('index'))

