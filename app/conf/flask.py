#!/usr/bin/env python

"""Global configuration module."""

# General imports

from os.path import abspath, dirname, join, pardir

# Global variables

APPLICATION_FOLDER = abspath(join(dirname(__file__), pardir))
AUTHORIZED_EMAILS = [
    'ninecoast@gmail.com',
]

# App configuration objects

class BaseConfig(object):

    DEBUG = False
    SECRET_KEY = 'replace_this_with_a_key'
    APP_DB_URL = 'sqlite:///%s/db/app.sqlite' % APPLICATION_FOLDER
    TESTING = False

class DebugConfig(BaseConfig):

    DEBUG = True
    APP_DB_URL = 'sqlite:///%s/db/app_dev.sqlite' % APPLICATION_FOLDER
    AUTH_DB_URL = 'sqlite:///%s/db/auth_dev.sqlite' % APPLICATION_FOLDER
    TESTING = False

# Auth blueprint configuration

class AuthConfig(object):

    CLIENT_ID = "727771047328-orosiiaun16cf0p6q8sfal3dema77hq4.apps.googleusercontent.com"
    CLIENT_SECRET = "kdZOow_-1502o-KC6SsgR5AE"
    REDIRECT_URI = 'http://nncsts.com:5000/oauth2callback'
