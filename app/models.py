#!/usr/bin/env python

"""Persistent classes."""

# Logging

import logging

logger = logging.getLogger(__name__)

# General imports

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.orm import backref, relationship

# App level imports

from app.core.database import Base
from app.core.util import Loggable

# Models
# ======

