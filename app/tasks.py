#!/usr/bin/env python

"""Asychronous jobs."""

import logging

logger = logging.getLogger(__name__)

# General imports

from time import sleep

# App level import

from app.core.celery import celery, CurrentJob
from app.core.database import Db

# Tasks
# =====

@celery.task()
def do_something():
    job = CurrentJob()
    job.context('Started...')
    print 'hi'
    sleep(5)
    job.context('Finished!')
