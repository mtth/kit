#!/usr/bin/env python

from __future__ import absolute_import

from celery import Celery
from celery.signals import worker_process_init, after_setup_logger
from celery.task import periodic_task
from logging.config import dictConfig

from ..project import current_project

celery = Celery()
celery.conf.update(current_project.CELERY_CONFIG.generate(current_project))
celery.periodic_task = periodic_task

@after_setup_logger.connect
def after_setup_logger_handler(logger, loglevel, logfile, **kwrds):
    """Setting up logger configuration for the worker."""
    dictConfig(current_project.LOGGER_CONFIG.generate(current_project))

@worker_process_init.connect
def create_worker_connection(*args, **kwargs):
  """Initialize database connection.

  This has to be done after the worker processes have been started otherwise
  the connection will fail.

  """
  current_project.db.create_connection()

current_project.celery = celery
