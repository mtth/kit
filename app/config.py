#!/usr/bin/env python

"""Global configuration module."""

from os.path import dirname

APPLICATION_FOLDER = dirname(__file__)

class BaseConfig(object):

    DEBUG = False
    SECRET_KEY = ''
    SQLALCHEMY_DB_URL = 'sqlite:///db/main.sqlite'
    TESTING = False

class DebugConfig(BaseConfig):

    DEBUG = True
    SQLALCHEMY_DB_URL = 'sqlite:///db/main_dev.sqlite'
    TESTING = False

class CeleryBaseConfig(object):

    BROKER_URL = 'redis://localhost:6379/0'
    CELERY_DISABLE_RATE_LIMIT = True
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERYD_CONCURRENCY = 2
    CELERYD_PREFETCH_MULTIPLIER = 1

class CeleryDebugConfig(CeleryBaseConfig):

    BROKER_URL = 'redis://localhost:6379/1'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
    DEBUG = True
