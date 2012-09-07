#!/usr/bin/env python

"""Asychronous jobs."""

import logging
logger = logging.getLogger(__name__)

# General imports
from time import sleep

# App level import
from app.ext.celery import celery, CurrentJob
from app.ext.database import Db

# Tasks
# =====

@celery.task()
def do_something():
    job = CurrentJob()
    sleep(5)
    job.context('Doing something for 2 seconds.')
    sleep(2)
    job.context('Doing something for 5 seconds.')
    sleep(5)
    job.context('Doing something for 7 seconds.')
    sleep(7)
    job.context('Doing something for 1 seconds.')
    sleep(1)
