#!/usr/bin/env python

"""Global configuration module."""

# General imports

from os.path import abspath, dirname, join, pardir

# Global variables

APPLICATION_FOLDER = abspath(join(dirname(__file__), pardir))

# App configuration objects

class BaseConfig(object):

    APP_DB_URL = 'sqlite:///%s/db/app.sqlite' % APPLICATION_FOLDER
    DEBUG = False
    LOGGER_NAME = 'app'
    SECRET_KEY = 'replace_this_with_a_key'
    SERVER_NAME = 'nncsts.com:5000'
    TESTING = False

class DebugConfig(BaseConfig):

    APP_DB_URL = 'sqlite:///%s/db/app_dev.sqlite' % APPLICATION_FOLDER
    DEBUG = True
    TESTING = True

# Auth blueprint configuration

class AuthConfig(object):

    CLIENT_ID = "727771047328-orosiiaun16cf0p6q8sfal3dema77hq4.apps.googleusercontent.com"
    CLIENT_SECRET = "kdZOow_-1502o-KC6SsgR5AE"
    REDIRECT_URI = 'http://nncsts.com:5000/auth/oauth2callback'
