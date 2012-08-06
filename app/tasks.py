#!/usr/bin/env python

"""Asychronous jobs."""

import logging

logger = logging.getLogger(__name__)

# General imports

from datetime import datetime

from time import sleep

# App level import

import app.config as x
import app.celery as s
import app.models as m
import app.controllers as c

# Job tracking
# ============

@s.task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **kwrds):
    with c.Session() as session:
        task_name = task.name.rsplit('.', 1)[1]
        job = m.Job(task_id, task_name, args, kwargs)
        session.add(job)
        session.commit()

@s.task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kwrds):
    with c.Session() as session:
        job = session.query(m.Job).filter(
                m.Job.id == task_id
        ).first()
        job.end_time = datetime.now()
        job.state = state
        session.add(job)
        session.commit()

class CurrentJob(object):

    def __init__(self, session):
        self.session = session
        self.task = s.current_task
        self.job = session.query(m.Job).filter(
                m.Job.id == self.task.request.id
        ).first()
        self.models = self.get_models()

    def get_models(self):
        pass

    def info(self, context, progress=100, silent=False):
        self.job.context = context
        self.job.progress = progress
        if not silent:
            kwargs = ' : '.join(str(v) for f in self.models.values())
            logger.info('%s :: %s' % (kwargs, context))
        self.session.commit()

# Tasks
# =====

@s.celery.task()
def do_something():
    with c.Session as session:
        job = CurrentJob(session)
        job.info('Started...')
        sleep(5)
        job.info('Finished!')
