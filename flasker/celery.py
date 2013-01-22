#!/usr/bin/env

"""Celery configuration module."""

# General imports

from __future__ import absolute_import

from celery import Celery
from celery.signals import worker_process_init, after_setup_logger
from celery.task import periodic_task
from logging.config import dictConfig

from app.core.config import LoggerConfig
from app.core.database import db

# Celery instantiation
# ====================

celery = Celery()
celery.periodic_task = periodic_task

# Setup handlers
# ==============

@after_setup_logger.connect
def after_setup_logger_handler(logger, loglevel, logfile, **kwrds):
    """Setting up logger configuration for the worker."""
    if celery.conf['DEBUG']:
        dictConfig(LoggerConfig.DEBUG_LOGGER_CONFIG)
    else:
        dictConfig(LoggerConfig.LOGGER_CONFIG)

# Connect to the database once the workers are initialized

def create_worker_connection(*args, **kwargs):
  """Initialize database connection.

  This has to be done after the worker processes have been started otherwise
  the connection will fail.

  """
  db.create_connection(debug=celery.conf['DEBUG'])

worker_process_init.connect(create_worker_connection)

