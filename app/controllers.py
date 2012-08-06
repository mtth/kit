#!/usr/bin/env python

"""The engine behind it all."""

# Logger

import logging

logger = logging.getLogger(__name__)

# General imports

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# App level imports

import app.config as x
import app.models as m

# Session handling
# ================

class Session(object):

    """Session handling.

    Usage inside the app::

        with Session() as session:
            # do stuff

    """

    def __enter__(self):
        return self.Session()

    def __exit__(self):
        self.Session.remove()

    @classmethod
    def initialize_db(cls, debug=False):
        """Initialize database connection."""
        if debug:
            engine = create_engine(
                    x.DebugConfig.APP_DB_URL,
                    pool_recycle=3600
            )
        else:
            engine = create_engine(
                    x.BaseConfig.APP_DB_URL,
                    pool_recycle=3600
            )
        m.Base.metadata.create_all(engine, checkfirst=True)
        cls.Session = scoped_session(sessionmaker(bind=engine))

# Controllers
# ===========


