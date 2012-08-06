#!/usr/bin/env python

"""This is where the auth magic happens."""

# Logger

import logging

logger = logging.getLogger(__name__)

# General imports

from flask import request

from json import loads

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from urllib import urlencode
from urllib2 import Request, urlopen

# Blueprint level imports

import models as m

# App level imports

import app.config as x

# Session handling
# ================

class Session(object):

    """Session handling.

    Usage inside the app::

        with Session() as session:
            # do stuff

    """

    def __enter__(self):
        return self.Session()

    def __exit__(self):
        self.Session.remove()

    @classmethod
    def initialize_db(cls, debug=False):
        """Initialize database connection."""
        if debug:
            engine = create_engine(
                    x.DebugConfig.AUTH_DB_URL,
                    pool_recycle=3600
            )
        else:
            engine = create_engine(
                    x.BaseConfig.AUTH_DB_URL,
                    pool_recycle=3600
            )
        m.Base.metadata.create_all(engine, checkfirst=True)
        cls.Session = scoped_session(sessionmaker(bind=engine))

# Google API helpers
# ==================

class OAuth:

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
    CLIENT_ID = "469814544301.apps.googleusercontent.com"
    CLIENT_SECRET = "MQ_HNDiwnYiWRCquXIj2G03i"
    REDIRECT_URI = 'http://nncsts.com:5000/oauth2callback'
    GRANT_TYPE = "authorization_code"
    ACCESS_TYPE = "offline"

def get_params():
    """Builds the dictionary of parameters required the API request.

    :rtype: dict

    """
    if 'next' in request.args:
        state = request.args['next']
    else:
        state = '/'
    return {'scope': OAuth.SCOPES['email'],
            'redirect_uri': OAuth.REDIRECT_URI,
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
