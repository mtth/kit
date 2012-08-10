#!/usr/bin/env python

"""The engine behind it all."""

# Logger

import logging

logger = logging.getLogger(__name__)

# General imports

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

# App level imports

from app.conf.flask import BaseConfig, DebugConfig

# SQLAlchemy setup
# ================

Base = declarative_base()

# Session handling
# ================

class Session(object):

    """Session handling.

    Usage inside the app::

        with Session() as session:
            # do stuff

    """

    debug = False

    def __enter__(self):
        try:
            return self.Session()
        except:
            raise Exception("The database connection needs to "
                            "be initialized before doing this.")

    def __exit__(self, type, value, traceback):
        self.Session.remove()

    @classmethod
    def initialize_db(cls, **kwrds):
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
        cls.Session = scoped_session(sessionmaker(bind=engine))

