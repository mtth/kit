#!/usr/bin/env python

"""Persistent classes."""

# Logging

import logging

logger = logging.getLogger(__name__)

# General imports

from flask.ext.login import UserMixin

from sqlalchemy import Boolean, Column, DateTime, Integer, Unicode, String, Text
from sqlalchemy.orm import backref, relationship

# App level imports

from app.core.database import Base
from app.core.util import Loggable

class User(Base, Loggable, UserMixin):

    """User class.

    :param email: user gmail email
    :type email: string

    """

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(64), unique=True)

    logger = logger

    def __init__(self, email):
        self.email = email

    def __repr__(self):
        return '<User %r>' % self.email

    def get_id(self):
        """Necessary for Flask login extension."""
        return self.email

