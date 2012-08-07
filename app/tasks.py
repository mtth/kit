#!/usr/bin/env python

"""Asychronous jobs."""

import logging

logger = logging.getLogger(__name__)

# General imports

from time import sleep

# App level import

from app.core.celery import celery
from app.core.database import Session

# Tasks
# =====

@celery.task()
def do_something():
    with Session() as session:
        job = CurrentJob(session)
        job.info('Started...')
        sleep(5)
        job.info('Finished!')
