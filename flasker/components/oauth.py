#!/usr/bin/env python

"""This is where the auth magic happens."""

from flask import Blueprint, flash, request, redirect, render_template, url_for
from flask.ext.login import current_user, login_user, logout_user, LoginManager, UserMixin
from json import loads
from logging import getLogger
from os.path import abspath, join, dirname
from sqlalchemy import Column, Integer, String
from urllib import urlencode
from urllib2 import Request, urlopen

from ..project import current_project
from ..util import Base

logger = getLogger(__name__)

# Login manager instance
# ======================

login_manager = LoginManager()
login_manager.login_view = '/sign_in'
login_manager.login_message = ''

@login_manager.user_loader
def load_user(user_email):
    """Return the user from his email.

    :param user_email: user email
    :type user_email: string
    :rtype: User

    Necessary for flask.login module.
    
    """
    user = User.query.filter(
            User.email == user_email
    ).first()
    return user

# Google OAuth API helpers
# ========================

class OAuth(object):

    """Contains variables used for the Google authentication process."""

    ENDPOINTS = {
            'get_token_or_code': "https://accounts.google.com/o/oauth2/auth",
            'validate_token': "https://www.googleapis.com/oauth2/v1/tokeninfo",
            'get_token_from_code': "https://accounts.google.com/o/oauth2/token",
            'get_user_info': "https://www.googleapis.com/oauth2/v2/userinfo",
    }
    SCOPES = {
            'email': "https://www.googleapis.com/auth/userinfo.email",
            'profile': "https://www.googleapis.com/auth/userinfo.profile"
    }
    RESPONSE_TYPE = "token"
    GRANT_TYPE = "authorization_code"
    ACCESS_TYPE = "offline"
    CLIENT_ID = None # oauth_credentials['google_client']
    CLIENT_SECRET = None # oauth_credentials['google_secret']

def get_params():
    """Builds the dictionary of parameters required the API request.

    :rtype: dict

    """
    if 'next' in request.args:
        state = request.args['next']
    else:
        state = '/'
    return {'scope': OAuth.SCOPES['email'],
            'redirect_uri': request.url_root + 'oauth2callback',
            'response_type': OAuth.RESPONSE_TYPE,
            'state': state,
            'client_id': OAuth.CLIENT_ID}

def get_google_login_url():
    """Combines the endpoint with the parameters to generate the API url.

    :rtype: string

    """
    return (OAuth.ENDPOINTS['get_token_or_code'] + '?' + 
                           urlencode(get_params()))

def validate_token(token):
    """Checks if the token is valid.

    :param token: auth token
    :type token: string
    :rtype: boolean

    """
    url = OAuth.ENDPOINTS['validate_token'] + '?access_token=' + token
    req = Request(url)
    token_info = loads(urlopen(req).read())
    if 'error' in token_info:
        return False
    else:
        return True

def get_user_info_from_token(token):
    """Grabs user email from token.

    :param token: auth token
    :type token: string
    :rtype: dict

    """
    url = OAuth.ENDPOINTS['get_user_info']
    headers = {'Authorization': 'Bearer ' + token}
    req = Request(url, headers=headers)
    res = loads(urlopen(req).read())
    return res

# Model
# =====

class User(Base, UserMixin):

    """User class.

    :param email: user gmail email
    :type email: string

    """

    id = Column(Integer, primary_key=True)
    email = Column(String(64), unique=True)

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return '<User id=%r email=%r>' % (self.id, self.email)

    def get_id(self):
        """Necessary for Flask login extension."""
        return self.email

# Creating the Blueprint
# ======================

bp = Blueprint(
        'core',
        __name__,
        template_folder=abspath(join(dirname(__file__), 'templates'))
)

# Handlers
# ========

@bp.route('/sign_in')
def sign_in():
    """Sign in view.

    Generates the google login url (calling ``get_google_loging_url`` from the
    controller) and puts in in a nice picture to click on.

    """
    values = {
            'header': 'Hey, stranger',
            'color': 'primary',
            'sign_in_url': get_google_login_url()
    }
    return render_template('sign_in_out.html', **values)

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
    return render_template('get_token_from_hash.html', **values)

@bp.route('/catch_token')
def catch_token():
    """Catches the token and signs in the user if it passes validation.

    If the user got to the sign in page from an non anonymous authorized page
    he will be directly redirected there after sign in. Otherwise he will be
    redirected to the home page.

    """
    token = request.args['access_token']
    logger.debug('Successfully caught access token.')
    if not validate_token(token):
        logger.warn('Access token is invalid.')
        values = {
                'header': 'You broke it',
                'color': 'danger',
                'sign_in_url': get_google_login_url()
        }
        return render_template('sign_in_out.html', **values)
    logger.debug('Access token is valid.')
    user_infos = get_user_info_from_token(token)
    logger.debug('Gathered user infos successfully.')
    user = User.query.filter(
            User.email == user_infos['email']
    ).first()
    if user:
        login_user(user)
        user.info('Signed in.')
        return redirect(request.args['state'])
    else:
        logger.warn('%s tried to sign in.' % user_infos['email'])
        values = {
                'header': 'Have we met?',
                'color': 'warning',
                'sign_in_url': get_google_login_url()
        }
        return render_template('sign_in_out.html', **values)
        
@bp.route('/sign_out')
def sign_out():
    """Sign out.

    Redirects to the home page after a successful sign out.

    """
    if current_user.is_authenticated():
        current_user.info('Signed out.')
        logout_user()
    values = {
            'header': 'Bye, friend',
            'color': 'success',
            'sign_in_url': get_google_login_url()
    }
    return render_template('sign_in_out.html', **values)

def make(credentials):
  OAuth.CLIENT_ID = credentials
  OAuth.CLIENT_SECRET = ''
  return {'bp': bp, 'login_manager': login_manager}

