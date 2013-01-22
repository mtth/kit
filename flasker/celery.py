#!/usr/bin/env

"""Celery configuration module."""

from __future__ import absolute_import

from celery import Celery
from celery.signals import worker_process_init, after_setup_logger
from celery.task import periodic_task
from logging.config import dictConfig

# Celery instantiation
# ====================

def make(celery, db, logger_config):

  celery.periodic_task = periodic_task

  # Setup handlers

  @after_setup_logger.connect
  def after_setup_logger_handler(logger, loglevel, logfile, **kwrds):
      """Setting up logger configuration for the worker."""
      dictConfig(logger_config)

  # Connect to the database once the workers are initialized

  def create_worker_connection(*args, **kwargs):
    """Initialize database connection.

    This has to be done after the worker processes have been started otherwise
    the connection will fail.

    """
    db.create_connection()

  if db:
    worker_process_init.connect(create_worker_connection)

