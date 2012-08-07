#!/usr/bin/env

"""Celery configuration module."""

# General imports

from __future__ import absolute_import

from celery import Celery, current_task
from celery.signals import celeryd_init, task_postrun, task_prerun, worker_process_init

# App level imports

from app.core.database import Session
from app.conf.celery import CeleryBaseConfig

# Celery instantiation
# ====================

celery = Celery()

def initialize_db(**kwargs):
    if celery.conf:
        pass

@celeryd_init.connect
def handler(sender=None, conf=None, **kwrds):
    print 'hi', celery.conf['BROKER_URL']

# if 'production' in __file__:
#     celery.config_from_object(x.CeleryBaseConfig)
#         Session.initialize_db()
# else:
#     celery.config_from_object(x.CeleryDebugConfig)
#     def initialize_db(**kwargs):
#         Session.initialize_db(debug=True)

# Connect to the database once the workers are initialized
# worker_process_init.connect(initialize_db)

# Job tracking
# ============

@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **kwrds):
    with Session() as session:
        task_name = task.name.rsplit('.', 1)[1]
        job = m.Job(task_id, task_name, args, kwargs)
        session.add(job)
        session.commit()

@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kwrds):
    with Session() as session:
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
        self.task = current_task
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

@celery.task()
def do_something_else():
    pass
