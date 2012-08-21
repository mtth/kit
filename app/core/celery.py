#!/usr/bin/env

"""Celery configuration module."""

# General imports

from __future__ import absolute_import

from logging.config import dictConfig

from celery import Celery, current_task
from celery.signals import celeryd_init, task_failure, task_postrun, \
task_prerun, task_success, worker_process_init, after_setup_logger
from datetime import datetime
from time import time

# App level imports

from app.config.logging import DEBUG_LOGGER_CONFIG, LOGGER_CONFIG
from app.core.database import Db
from app.jobs.models import Job

# Celery instantiation
# ====================

celery = Celery()

# Setup handlers
# ==============

@celeryd_init.connect
def celeryd_init_handler(sender=None, conf=None, **kwrds):
    """In preparation for the database initialization on the worker."""
    Db.debug = conf['DEBUG']

@after_setup_logger.connect
def after_setup_logger_handler(logger, loglevel, logfile, **kwrds):
    """Setting up logger configuration for the worker."""
    if Db.debug:
        dictConfig(DEBUG_LOGGER_CONFIG)
    else:
        dictConfig(LOGGER_CONFIG)

# Connect to the database once the workers are initialized
worker_process_init.connect(Db.initialize)

# Job tracking
# ============

# Signal handlers
# ---------------

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **kwrds):
    """Called right before the worker starts a task."""
    parameters = {
            'args': args,
            'kwargs': kwargs
    }
    job = Job(task_id, task.name, parameters)
    Db.session.add(job)
    Db.session.commit()

@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback,
        einfo, **kwrds):
    """Called if task failed."""
    job = CurrentJob(task_id)
    job.context(traceback)

@task_success.connect
def task_success_handler(result, **kwrds):
    """Called if task succeeds."""
    job = CurrentJob()
    job.context('Success!')

@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kwrds):
    """Called last after a task terminates (successfully or not)."""
    job = CurrentJob(task_id)
    job.job.end_time = datetime.now()
    job.job.state = state
    Db.session.add(job.job)
    Db.session.commit()
    Db.dismantle()

# Current Job
# -----------

class CurrentJob(object):

    """Helper class to help job tracking and progress updates.

    Usage::

        @celery.task()
        def do_something():
            job = CurrentJob()
            job.context('This fantastic job just started...', 10)
            # do stuff
            job.context('Success!')

    """

    def __init__(self, task_id=None):
        task_id = task_id or current_task.request.id
        self.job = Job.query.get(task_id)

    def context(self, context, progress=100, loglevel='info'):
        """Method to update a job's progress.

        Performs several actions:
            * Stores the new context and progress on the job instance
            * Logs the new context at the prompted loglevel (if not `None`)
            * Stores statistics on how long each context took

        """
        previous_context = self.job.context
        if previous_context != unicode(context):
            context_start = self.job.statistics['last_context_update']
            context_end = time()
            runtime_breakdown = self.job.statistics['runtime_breakdown']
            runtime_breakdown.append((
                    previous_context,
                    context_end - context_start
            ))
            self.job.statistics['runtime_breakdown'] = runtime_breakdown
            self.job.statistics['last_context_update'] = context_end
            self.job.context = context
        self.job.progress = progress
        if loglevel:
            action = getattr(self.job, loglevel)
            action(context)
        Db.session.commit()

