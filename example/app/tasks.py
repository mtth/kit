#!/usr/bin/env python

from flasker import current_project
from time import sleep

celery = current_project.celery

@celery.task
def do_something():
  """Placeholder task.
  
  This function will be executed outside the app, in the celery worker.

  """
  sleep(10)

@celery.periodic_task(run_every=3600)
def do_something_every_hour():
  """Placeholder periodic task.

  This function will be executed by the worker every hour (if the scheduler
  is activated).

  """
  sleep(5)

