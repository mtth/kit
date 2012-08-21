#!/usr/bin/env python

"""Persistent classes."""

# Logging

from logging import getLogger

logger = getLogger(__name__)

# General imports

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer
from time import time

# App level imports

from app.core.database import Base, MutableDict, JSONEncodedDict
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
    _parameters = Column(MutableDict.as_mutable(JSONEncodedDict))
    infos = Column(MutableDict.as_mutable(JSONEncodedDict))

    def __init__(self, task_id, task_name, parameters):
        self.id = task_id
        self.name = task_name
        self.start_time = datetime.now()
        self.context = 'Started...'
        self.parameters = parameters
        self.infos = {
                'runtime_breakdown': [],
                'runtime_estimation': 0,
                'last_context_update': time()
        }
        self.debug('Created.')

    def __repr__(self):
        """To be extended to include the name and args, kwargs."""
        return '<Job id=%s>' % self.id

    @property
    def parameters(self):
        return dict((k, v) for k, v in self._parameters.items() if v)

    @parameters.setter
    def parameters(self, value):
        self._parameters = value

    def get_models(self):
        """Get the objects that are inputs to the task.

        This uses a particular structure for calling tasks: kwargs are reserved
        for arguments that represent models classes and they must be called as
        follows::

            kwargs = {
                    'ModelClass': primary_key,
                    # ...
            }

        """
        pass

    @property
    def runtime(self):
        """Current job runtime."""
        if self.end_time:
            return (self.end_time - self.start_time).seconds
        else:
            return (datetime.now() - self.start_time).seconds
