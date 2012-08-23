#!/usr/bin/env python

"""Persistent classes."""

# Logging

from logging import getLogger

logger = getLogger(__name__)

# General imports

from datetime import datetime
from flask import url_for
from sqlalchemy import Column, String, DateTime, Text, Integer
from time import time

# App level imports

from app.core.database import Base, JSONEncodedDict
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
    state = Column(String(8), default='RUNNING')
    progress = Column(Integer, default=0)
    context = Column(Text, default='Started...')
    _parameters = Column(JSONEncodedDict)
    infos = Column(JSONEncodedDict)

    def __init__(self, task_id, task_name, parameters):
        self.id = task_id
        self.name = task_name
        self.start_time = datetime.now()
        self.context = 'Started...'
        self.parameters = parameters
        self.infos = {
                'runtime_breakdown': [],
                'last_context_update': time()
        }
        self.debug('Created.')

    def __repr__(self):
        """To be extended to include the name and args, kwargs. Maybe."""
        return '<Job id=%s>' % self.id

    @property
    def parameters(self):
        """We do some formatting before outputting the parameters here."""
        params = self._parameters
        rv = ', '.join([str(v) for v in params['args']])
        rv += ', ' if rv else ''
        rv += ', '.join('%s=%s' % (k,v) for k, v in params['kwargs'])
        return rv

    @parameters.setter
    def parameters(self, value):
        """Setter for parameters."""
        self._parameters = value

    @property
    def runtime(self):
        """Current job runtime."""
        end = self.end_time if self.end_time else datetime.now()
        delta = end - self.start_time
        return delta.seconds + float(delta.microseconds) / 1e6

    @property
    def url(self):
        """Url for job page."""
        return url_for('.job', job_id=self.id)
