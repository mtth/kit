#!/usr/bin/env

"""Celery configuration module."""

# General imports

from __future__ import absolute_import

from celery import Celery, current_task
from celery.signals import celeryd_init, task_failure, task_postrun, \
task_prerun, task_success, worker_process_init, after_setup_logger
from datetime import datetime
from logging.config import dictConfig
from sqlalchemy import Boolean, Column, DateTime, Integer, Unicode, String, Text
from sqlalchemy.orm import backref, relationship
from time import time

# App level imports

from app.core.config import LoggerConfig
from app.core.database import db

# Celery instantiation
# ====================

celery = Celery()

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

