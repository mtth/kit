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
from sqlalchemy.orm import class_mapper, Query, scoped_session, sessionmaker
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.types import TypeDecorator, Text

# App level imports

from app.config.flask import BaseConfig, DebugConfig

# SQLAlchemy setup
# ================

Base = declarative_base()

# Inspired by Flask-SQLAlchemy
# ============================

class Pagination(object):
    """Internal helper class returned by :meth:`BaseQuery.paginate`.  You
    can also construct it from any other SQLAlchemy query object if you are
    working with other libraries.  Additionally it is possible to pass `None`
    as query object in which case the :meth:`prev` and :meth:`next` will
    no longer work.
    """

    def __init__(self, query, page, per_page, total, items):
        #: the unlimited query object that was used to create this
        #: pagination object.
        self.query = query
        #: the current page number (1 indexed)
        self.page = page
        #: the number of items to be displayed on a page.
        self.per_page = per_page
        #: the total number of items matching the query
        self.total = total
        #: the items for the current page
        self.items = items

    @property
    def pages(self):
        """The total number of pages"""
        return int(ceil(self.total / float(self.per_page)))

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.query.paginate(self.page - 1, self.per_page, error_out)

    @property
    def prev_num(self):
        """Number of the previous page."""
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.query.paginate(self.page + 1, self.per_page, error_out)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.

        """
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


class BaseQuery(Query):
    """The default query object used for models, and exposed as
    :attr:`~SQLAlchemy.Query`. This can be subclassed and
    replaced for individual models by setting the :attr:`~Model.query_class`
    attribute.  This is a subclass of a standard SQLAlchemy
    :class:`~sqlalchemy.orm.query.Query` class and has all the methods of a
    standard query as well.

    """

    def get_or_404(self, ident):
        """Like :meth:`get` but aborts with 404 if not found instead of
        returning `None`.
        """
        rv = self.get(ident)
        if rv is None:
            abort(404)
        return rv

    def first_or_404(self):
        """Like :meth:`first` but aborts with 404 if not found instead of
        returning `None`.
        """
        rv = self.first()
        if rv is None:
            abort(404)
        return rv

    def paginate(self, page, per_page=20, error_out=True):
        """Returns `per_page` items from page `page`.  By default it will
        abort with 404 if no items were found and the page was larger than
        1.  This behavor can be disabled by setting `error_out` to `False`.

        Returns an :class:`Pagination` object.
        """
        if error_out and page < 1:
            abort(404)
        items = self.limit(per_page).offset((page - 1) * per_page).all()
        if not items and page != 1 and error_out:
            abort(404)
        return Pagination(self, page, per_page, self.count(), items)

class _QueryProperty(object):

    def __init__(self, Db):
        self.Db = Db

    def __get__(self, obj, cls):
        try:
            mapper = class_mapper(cls)
            if mapper:
                return BaseQuery(mapper, session=self.Db.session())
        except UnmappedClassError:
            return None

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
    def initialize(cls, app=None, **kwrds):
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
        Base.query = _QueryProperty(cls)
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
        return dumps(value) if value else {}

    def process_result_value(self, value, dialect):
        return loads(value) if value else {}

class MutableDict(Mutable, dict):

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
        
# Attach the mutation listeners to the JSONEncodedDict class globally
MutableDict.associate_with(JSONEncodedDict)
