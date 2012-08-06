#!/usr/bin/env python

"""Global configuration module."""

# General imports

from os.path import dirname

# Global variables

APPLICATION_FOLDER = dirname(__file__)

# App configuration objects

class BaseConfig(object):

    DEBUG = False
    SECRET_KEY = ''
    APP_DB_URL = 'sqlite:///%s/db/app.sqlite' % APPLICATION_FOLDER
    AUTH_DB_URL = 'sqlite:///%s/db/auth.sqlite' % APPLICATION_FOLDER
    TESTING = False

class DebugConfig(BaseConfig):

    DEBUG = True
    APP_DB_URL = 'sqlite:///%s/db/app_dev.sqlite' % APPLICATION_FOLDER
    AUTH_DB_URL = 'sqlite:///%s/db/auth_dev.sqlite' % APPLICATION_FOLDER
    TESTING = False

# Celery worker configuration

class CeleryBaseConfig(object):

    BROKER_URL = 'redis://localhost:6379/0'
    CELERY_DISABLE_RATE_LIMIT = True
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERYD_CONCURRENCY = 3
    CELERYD_PREFETCH_MULTIPLIER = 1

class CeleryDebugConfig(CeleryBaseConfig):

    BROKER_URL = 'redis://localhost:6379/1'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
    DEBUG = True

# Auth blueprint configuration

class AuthConfig(object):

    AUTH_DB_URL = 'sqlite:///%s/db/auth.sqlite' % APPLICATION_FOLDER

class DebugAuthConfig(AuthConfig):

    AUTH_DB_URL = 'sqlite:///%s/db/auth_dev.sqlite' % APPLICATION_FOLDER
