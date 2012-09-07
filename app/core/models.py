#!/usr/bin/env python

"""Persistent classes."""

# Logging

import logging

logger = logging.getLogger(__name__)

# General imports

from datetime import datetime
from flask import url_for
from flask.ext.login import current_user, UserMixin
from sqlalchemy import Boolean, Column, DateTime, Integer, Unicode, String, Text
from sqlalchemy.orm import backref, relationship
from time import time

# App level imports

from app.ext.database import Base, JSONEncodedDict
from app.ext.util import Jsonifiable, Loggable

class User(Base, UserMixin):

    """User class.

    :param email: user gmail email
    :type email: string

    """

    id = Column(Integer, primary_key=True)
    email = Column(String(64), unique=True)

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return '<User id=%r>' % self.id

    def __str__(self):
        return 'you' if current_user == self else self.email

    def get_id(self):
        """Necessary for Flask login extension."""
        return self.email

class Job(Base):

    """Celery jobs."""

    id = Column(Integer, primary_key=True)
    task_id = Column(String(64), unique=True)
    task_name = Column(String(64))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    state = Column(String(16), default='RUNNING')
    progress = Column(Integer, default=0)
    context = Column(String(64), default='Started...')
    parameters = Column(JSONEncodedDict)
    infos = Column(JSONEncodedDict)

    def __init__(self, task_id, task_name, parameters):
        self.task_id = task_id
        self.task_name = task_name
        self.start_time = datetime.now()
        self.parameters = parameters
        self.infos = {
                'runtime_breakdown': [],
                'last_context_update': time()
        }
        self.debug('Created.')

    def __repr__(self):
        """To be extended to include the name and args, kwargs. Maybe."""
        return '<Job id=%r>' % self.id

    @property
    def parameters_list(self):
        """We do some formatting before outputting the parameters here."""
        params = self.parameters
        rv = ', '.join([str(v) for v in params['args']])
        rv += ', ' if rv else ''
        rv += ', '.join('%s=%s' % (k,v) for k, v in params['kwargs'])
        return rv

    @property
    def runtime(self):
        """Current job runtime."""
        end = self.end_time if self.end_time else datetime.now()
        delta = end - self.start_time
        return delta.seconds + float(delta.microseconds) / 1e6
