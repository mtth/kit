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

from app.core.config import DEBUG_LOGGER_CONFIG, LOGGER_CONFIG
from app.core.database import Base, Db, JSONEncodedDict

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
            # do stuff
            job.context('This fantastic job is doing cool stuff...', 10)
            # do some other great stuff

    """

    def __init__(self, task_id=None):
        task_id = task_id or current_task.request.id
        self.job = Job.query.filter(Job.task_id == task_id).one()

    def context(self, context, progress=100, loglevel='info'):
        """Method to update a job's progress.

        Performs several actions:
            * Stores the new context and progress on the job instance
            * Logs the new context at the prompted loglevel (if not `None`)
            * Stores statistics on how long each context took

        """
        previous_context = self.job.context
        if previous_context != unicode(context):
            context_start = self.job.infos['last_context_update']
            context_end = time()
            runtime_breakdown = self.job.infos['runtime_breakdown']
            runtime_breakdown.append((
                    previous_context,
                    context_end - context_start
            ))
            self.job.infos['runtime_breakdown'] = runtime_breakdown
            self.job.infos['last_context_update'] = context_end
            self.job.context = context
        self.job.progress = progress
        if loglevel:
            action = getattr(self.job, loglevel)
            action(context)
        Db.session.commit()

# Model

class Job(Base):

    """Celery jobs."""

    id = Column(Integer, primary_key=True)
    task_id = Column(String(64), unique=True)
    task_name = Column(String(64))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    state = Column(String(16), default='RUNNING')
    progress = Column(Integer, default=0)
    context = Column(String(64), default='Started...')
    parameters = Column(JSONEncodedDict)
    infos = Column(JSONEncodedDict)

    def __init__(self, task_id, task_name, parameters):
        self.task_id = task_id
        self.task_name = task_name
        self.start_time = datetime.now()
        self.parameters = parameters
        self.infos = {
                'runtime_breakdown': [],
                'last_context_update': time()
        }
        self.debug('Created.')

    def __repr__(self):
        """To be extended to include the name and args, kwargs. Maybe."""
        return '<Job id=%r>' % self.id

    @property
    def parameters_list(self):
        """We do some formatting before outputting the parameters here."""
        params = self.parameters
        rv = ', '.join([str(v) for v in params['args']])
        rv += ', ' if rv else ''
        rv += ', '.join('%s=%s' % (k,v) for k, v in params['kwargs'])
        return rv

    @property
    def runtime(self):
        """Current job runtime."""
        end = self.end_time if self.end_time else datetime.now()
        delta = end - self.start_time
        return delta.seconds + float(delta.microseconds) / 1e6
