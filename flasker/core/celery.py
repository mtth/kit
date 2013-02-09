#!/usr/bin/env python

"""Creating the Celery application."""

from __future__ import absolute_import

from celery import Celery
from celery.signals import worker_process_init
from celery.task import periodic_task

from ..project import current_project

pj = current_project

celery = Celery()
celery.conf.update(pj.config['CELERY'])
celery.periodic_task = periodic_task

@worker_process_init.connect
def create_worker_connection(*args, **kwargs):
  """Initialize database connection.

  This has to be done after the worker processes have been started otherwise
  the connection will fail.

  """
  pj.setup_database_connection(celery=True)

pj.celery = celery
