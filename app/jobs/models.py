#!/usr/bin/env python

"""Persistent classes."""

# Logging

import logging

logger = logging.getLogger(__name__)

# General imports

from datetime import datetime

from json import dumps, loads

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.orm import backref, relationship

# App level imports

from app.core.database import Base
from app.core.util import Jsonifiable, Loggable

# The models
# ==========

class Job(Base, Jsonifiable, Loggable):

    """Celery jobs."""

    __tablename__ = 'jobs'

    logger = logger

    id = Column(String(64), primary_key=True)
    name = Column(String(64))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    estimated_runtime = Column(Integer)
    state = Column(String(16))
    progress = Column(Integer)
    context = Column(Text)

    def __init__(self, task_id, task_name, args, kwargs):
        self.id = task_id
        self.name = task_name
        self.start_time = datetime.now()
        self.state = 'RUNNING'
        self.progress = 0
        self._args = dumps(args)
        self._kwargs = dumps(kwargs)
        self.debug('Created.')

    def __repr__(self):
        """To be extended to include the name and args, kwargs."""
        return '<Job id=%s>' % self.id

    @property
    def args(self):
        return loads(self._args)

    @property
    def kwargs(self):
        return loads(self._kwargs)
