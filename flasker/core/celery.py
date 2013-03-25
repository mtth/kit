#!/usr/bin/env python

"""Creating the Celery application."""

from __future__ import absolute_import

from celery import Celery
from celery.signals import task_postrun, worker_process_init
from celery.task import periodic_task


def make_celery_app(project):

  conf = {k: v for k, v in project.config['CELERY'].items()}

  celery = Celery()
  celery.conf.update(conf)
  celery.periodic_task = periodic_task

  @worker_process_init.connect
  def create_worker_connection(*args, **kwargs):
    """Initialize database connection.

    This has to be done after the worker processes have been started otherwise
    the connection will fail.

    """
    project._setup_database_connection()

  @task_postrun.connect
  def task_postrun_handler(*args, **kwargs):
    project._dismantle_database_connections()

  return celery

