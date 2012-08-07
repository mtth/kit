#!/usr/bin/env python

"""Persistent classes."""

# Logging

import logging

logger = logging.getLogger(__name__)

# General imports

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

# App level imports

from app.core.util import Loggable

import app.conf as x

# SQLAlchemy setup
# ================

Base = declarative_base()

# The models
# ==========

class Job(Base, Loggable):

    """Celery jobs."""

    __tablename__ = 'jobs'

    id = Column(String(64), primary_key=True)
    task_name = Column(String(64))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    estimated_runtime = Column(Integer)
    state = Column(String(16))
    progress = Column(Integer)
    context = Column(Text)

    def __init__(self, task_name, args, kwargs):
        self.id = id
        self.task_name = task_name
        self.start_time = datetime.now()
        self.state = 'RUNNING'
        self.progress = 0
        self._args = dumps(args)
        self._kwargs = dumps(kwargs)
        self.debug('Created.')

    @property
    def args(self):
        return loads(self._args)

    @property
    def kwargs(self):
        return loads(self._kwargs)
