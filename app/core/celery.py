#!/usr/bin/env

"""Celery configuration module."""

# General imports

from __future__ import absolute_import

from logging.config import dictConfig

from celery import Celery, current_task
from celery.signals import celeryd_init, task_postrun, task_prerun, \
worker_process_init, after_setup_logger

from datetime import datetime

# App level imports

from app.config.logging import DEBUG_LOGGER_CONFIG, LOGGER_CONFIG
from app.core.database import Session
from app.jobs.models import Job

# Celery instantiation
# ====================

celery = Celery()

@celeryd_init.connect
def handler(sender=None, conf=None, **kwrds):
    """In preparation for the database initialization on the worker."""
    Session.debug = conf['DEBUG']

# Connect to the database once the workers are initialized
worker_process_init.connect(Session.initialize_db)

@after_setup_logger.connect
def after_setup_logger_handler(logger, loglevel, logfile, **kwrds):
    """Setting up logger configuration for the worker."""
    if Session.debug:
        dictConfig(DEBUG_LOGGER_CONFIG)
    else:
        dictConfig(LOGGER_CONFIG)

# Job tracking
# ============

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **kwrds):
    with Session() as session:
        task_name = task.name.rsplit('.', 1)[1]
        job = Job(task_id, task_name, args, kwargs)
        session.add(job)
        session.commit()

@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kwrds):
    with Session() as session:
        job = session.query(Job).filter(
                Job.id == task_id
        ).first()
        job.end_time = datetime.now()
        job.state = state
        session.add(job)
        session.commit()

class CurrentJob():

    def __init__(self, session):
        self.session = session
        self.task = current_task
        self.job = session.query(Job).filter(
                Job.id == self.task.request.id
        ).first()

    def progress(self, context, progress=100, loglevel='info'):
        self.job.context = context
        self.job.progress = progress
        if loglevel:
            action = getattr(self.job, loglevel)
            action(context)
        self.session.commit()

