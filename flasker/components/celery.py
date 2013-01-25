#!/usr/bin/env python

from __future__ import absolute_import

from celery import Celery
from celery.signals import worker_process_init, after_setup_logger
from celery.task import periodic_task
from logging.config import dictConfig

from ..project import current_project

pj = current_project

celery = Celery()
celery.conf.update(pj.config['CELERY'])
celery.periodic_task = periodic_task

@after_setup_logger.connect
def after_setup_logger_handler(logger, loglevel, logfile, **kwrds):
    """Setting up logger configuration for the worker."""
    # dictConfig(pj.LOGGER_CONFIG.generate(pj))
    pass

@worker_process_init.connect
def create_worker_connection(*args, **kwargs):
  """Initialize database connection.

  This has to be done after the worker processes have been started otherwise
  the connection will fail.

  """
  pj.db.create_connection()

pj.celery = celery
