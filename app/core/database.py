#!/usr/bin/env python

"""The engine behind it all."""

# Logger

import logging

logger = logging.getLogger(__name__)

# General imports

from json import dumps, loads
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.types import TypeDecorator, Text

# App level imports

from app.config.flask import BaseConfig, DebugConfig

# SQLAlchemy setup
# ================

Base = declarative_base()

# Session handling
# ================

class Db(object):

    """Session handling.

    Usage inside the app::

        Db.session.add(something)
        Db.session.commit()

    Session creation and destruction is handled out of the box.

    Or (but not recommended)::

        with Db() as session:
            # do stuff

    """

    debug = False

    def __enter__(self):
        return self.session()

    def __exit__(self, type, value, traceback):
        self.session.remove()

    @classmethod
    def initialize(cls, app, **kwrds):
        """Initialize database connection."""
        if cls.debug:
            engine = create_engine(
                    DebugConfig.APP_DB_URL,
                    pool_recycle=3600
            )
        else:
            engine = create_engine(
                    BaseConfig.APP_DB_URL,
                    pool_recycle=3600
            )
        Base.metadata.create_all(engine, checkfirst=True)
        cls.session = scoped_session(sessionmaker(bind=engine))
        Base.query = cls.session.query_property()
        if app:
            @app.teardown_request
            def teardown_request_handler(exception=None):
                """Called after app requests return."""
                cls.dismantle()

    @classmethod
    def dismantle(cls, **kwrds):
        """Remove database connection.

        Has to be called after app request/job terminates or connections
        will leak.

        """
        cls.session.remove()

# Helper classes
# ==============

class JSONEncodedDict(TypeDecorator):

    """Represents an immutable structure as a JSON encoded dict."""

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = loads(value)
        return value

class Features(Mutable, dict):

    """Used with JSONEncoded dict to be able to track updates.

    Usage is similar to other SQLAlchemy Column types::

        features = Column(Features.as_mutable(JSONEncodedDict))

    """

    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionaries to Features."""
        if not isinstance(value, cls):
            if isinstance(value, dict):
                return cls(value)
            return Mutable.coerce(key, value) # this will raise an error
        else:
            return value

    def update(self, *args, **kwargs):
        """Detect dictionary update events and emit change events."""
        dict.update(self, *args, **kwargs)
        self.changed()
        
    def __setitem__(self, key, value):
        """Detect dictionary set events and emit change events."""
        dict.__setitem__(self, key, value)
        self.changed()
        
    def __delitem__(self, key):
        """Detect dictionary del events and emit change events."""
        dict.__delitem__(self, key)
        self.changed()
        
