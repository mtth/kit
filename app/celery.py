#!/usr/bin/env

"""Celery configuration module."""

# General imports

from __future__ import absolute_import

from celery import Celery, chain, chord, current_task, group
from celery.signals import task_postrun, task_prerun, worker_process_init

# App level imports

import app.controllers as c
import app.config as x

# Celery instantiation
# ====================

celery = Celery()

if 'production' in __file__:
    celery.config_from_object(x.CeleryBaseConfig)
    def initialize_db(**kwargs):
        c.Session.initialize_db()
else:
    celery.config_from_object(x.CeleryDebugConfig)
    def initialize_db(**kwargs):
        c.Session.initialize_db(debug=True)

# Connect to the database once the workers are initialized
worker_process_init.connect(initialize_db)
