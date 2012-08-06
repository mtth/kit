#!/usr/bin/env python

"""Persistent classes."""

# Logging

import logging

logger = logging.getLogger(__name__)

# General imports

from datetime import datetime

from functools import partial

from json import dumps, loads

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

# App level imports

import app.config as x

# SQLAlchemy setup
# ================

Base = declarative_base()


# Helpers
# =======

class ExpandedBase(object):

    """To easily access stored instances properties and log stuff."""

    def jsonify(self):
        d = {}
        varnames = [
                e for e in dir(self)
                if not e.startswith('_')
                if not e == 'metadata'
        ]
        for varname in attributes:
            value = getattr(self, varname)
            if isinstance(value, (dict, float, int, str)):
                d[varname] = getattr(self, value)
            elif isinstance(value, datetime):
                d[varname] = getattr(self, str(value))
        return d

    def _logger(self, message, loglevel):
        action = getattr(logger, loglevel)
        return action('%s :: %s' % (self, message))

    def __getattr__(self, varname):
        if varname in ['debug', 'info', 'warn', 'error']:
            return partial(self._logger, loglevel=varname)
        else:
            raise AttributeError

# The models
# ==========

class Job(Base, ExpandedBase):

    """Celery jobs."""

    __tablename__ = 'jobs'

    id = Column(String(64), primary_key=True)
    task_name = Column(String(64))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    estimated_runtime = Column(Integer)
    state = Column(String(16))
    progress = Column(Integer)
    context = Column(String(64))

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
