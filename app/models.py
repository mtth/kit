#!/usr/bin/env python

"""Persistent classes."""

# Logging

import logging

logger = logging.getLogger(__name__)

# General imports

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.orm import backref, relationship

# App level imports

from app.core.models import Base
from app.core.util import Loggable

class Member(Base):

    __tablename__ = 'members'

    id = Column(Integer, primary_key=True)
    name = Column(String(64))

    def __init__(self, name):
        self.name = name
