#!/usr/bin/env python

"""Global configuration module."""

# Celery worker configuration

# from os.path import abspath, dirname, join, pardir
# 
# APPLICATION_FOLDER = abspath(join(dirname(__file__), pardir))
# APP_DB_URL = 'sqlite:///%s/db/app.sqlite' % APPLICATION_FOLDER
# DEBUG = False

BROKER_URL = 'redis://localhost:6379/0'
CELERY_DISABLE_RATE_LIMIT = True
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERYD_CONCURRENCY = 3
CELERYD_PREFETCH_MULTIPLIER = 1
CELERY_IMPORTS = (
        'app.core.celery',
        'app.tasks',
)
