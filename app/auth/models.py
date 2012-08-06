#!/usr/bin/env python

"""Persistent classes."""

import logging

logger = logging.getLogger(__name__)

# General imports

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.ext.declarative import declarative_base

# App level imports

import app.config as x

# SQLAlchemy setup
# ================

Base = declarative_base()

class User(Base):

    """User class.

    This class is pretty generic. Additional features will come from
    the other blueprints.

    :param email: user gmail email
    :type email: ``str``

    List of properties stored in the database:

    *   id
    *   email
    *   name
    *   is_admin

    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120))
    name = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean)

    def __init__(self, email):
        self.email = email
        self.name = ''
        self.is_admin = False

    def __repr__(self):
        return '<User %r>' % self.email

    def make_admin(self):
        """Make the user admin."""
        self.is_admin = True

    def get_id(self):
        """Necessary for Flask login extension."""
        return self.email
