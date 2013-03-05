#!/usr/bin/env python

from functools import partial
from random import randint
from sqlalchemy import Column, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import (backref as _backref, class_mapper, Query as _Query,
  relationship as _relationship)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty

from ..util import (Cacheable, to_json, 
  JSONEncodedDict, Loggable, uncamelcase, query_to_dataframe, query_to_records)


class ORM(object):

  """The main ORM extension.

  Responsible for adding the ``q`` and ``c`` query proxies on the model and
  configuring the project to use a custom ``Query`` class.

  There is currently a single option available:

  * ``CREATE_ALL`` to create tables for all models which don't already have one
    (defaults to ``True``).

  """

  def __init__(self, project, create_all=True):

    project._query_class = Query

    self.Model = declarative_base(cls=Base)
    self.backref = partial(_backref, query_class=Query)
    self.relationship = partial(_relationship, query_class=Query)

    @project.before_startup
    def handler(project):
      self.Model.q = _QueryProperty(project)
      self.Model.c = _CountProperty(project)
      if create_all:
        self.Model.metadata.create_all(project._engine, checkfirst=True)


class Query(_Query):

  """Base query class.

  The first two methods are from Flask-SQLAlchemy.

  """

  def get_or_404(self, model_id):
    """Like get but aborts with 404 if not found.

    :param model_id: the model's primary key
    :type model_id: varies
    :rtype: model or HTTPError
    
    """
    rv = self.get(model_id)
    if rv is None:
      abort(404)
    return rv

  def first_or_404(self):
    """Like first but aborts with 404 if not found.
    
    :param model_id: the model's primary key
    :type model_id: varies
    :rtype: model or HTTPError
    
    """
    rv = self.first()
    if rv is None:
      abort(404)
    return rv

  def random(self, n=1, dialect=None):
    """Returns n random model instances.

    :param n: the number of instances to return
    :type n: int
    :param dialect: the engine dialect (the implementation of random differs
      between MySQL and SQLite among others). By default will look up on the
      query for the dialect used. If no random function is available for the 
      chosen dialect, the fallback implementation uses total row count to 
      generate random offsets.
    :type dialect: str
    :rtype: model instances
    
    """
    if dialect is None:
      conn = self._connection_from_session()
      dialect = conn.dialect.name
    if dialect == 'mysql':
      rv = self.order_by(func.rand()).limit(n).all()
    elif dialect in ['sqlite', 'postgresql']:
      rv = self.order_by(func.random()).limit(n).all()
    else: # fallback implementation
      count = self.count()
      rv = [self.offset(randint(0, count - 1)).first() for _ in range(n)]
    if len(rv) == 1:
      return rv[0]
    return rv

  def to_dataframe(self, *args, **kwargs):
    """Loads a dataframe with the records from the query and returns it.

    Accepts the same arguments as ``flasker.util.query_to_dataframe``.
    Requires the ``pandas`` library to be installed.

    """
    return query_to_dataframe(self, *args, **kwargs)

  def to_records(self, *args, **kwargs):
    """Raw execute of the query into a generator."""
    return query_to_records(self, *args, **kwargs)


class _QueryProperty(object):

  """To make queries accessible directly on model classes."""

  def __init__(self, project):
    self.project = project

  def __get__(self, obj, cls):
    try:
      mapper = class_mapper(cls)
      if mapper:
        return Query(mapper, session=self.project.session())
    except UnmappedClassError:
      return None


class _CountProperty(object):

  """To make count queries directly accessible on model classes."""

  def __init__(self, project):
    self.project = project

  def __get__(self, obj, cls):
    try:
      mapper = class_mapper(cls)
      if mapper:
        session = self.project.session()
        return Query(func.count(cls), session=session).select_from(cls)
    except UnmappedClassError:
      return None


class Base(Cacheable, Loggable):

  """The SQLAlchemy base model with multiple helpers.

  Along with the methods described below, the following conveniences are
  provided:

  * the ``q`` query property

  * the ``c`` count query property. This will be much faster than issuing
    ``count()`` on a normal query on MySQL as it will bypass the use of a
    subquery.

  * Automatic table naming (to the model's class name uncamelcased with an
    extra s appended for good measure).

  * ``__repr__`` implementation with model class and primary keys

  * Caching (from ``flasker.util.Cacheable``)

  * Logging (from ``flasker.util.Loggable``)

  """

  _cache = Column(JSONEncodedDict)
  _json_depth = 0

  c = None
  q = None

  @classmethod
  def _get_columns(cls, show_private=False):
    columns = class_mapper(cls).columns
    if not show_private:
      columns = [c for c in columns if not c.key.startswith('_')]
    return columns

  @classmethod
  def _get_related_models(cls, show_private=False):
    return [
      (r.key, r.mapper.class_)
      for r in cls._get_relationships(show_private)
    ]

  @classmethod
  def _get_relationships(cls, show_private=False):
    rels =  class_mapper(cls).relationships.values()
    if not show_private:
      rels = [rel for rel in rels if not rel.key.startswith('_')]
    return rels

  @classmethod
  def retrieve(cls, flush_if_new=True, **kwargs):
    """Given constructor arguments will return a match or create one.

    :param kwargs: constructor arguments
    :rtype: tuple

    This method returns a tuple ``(model, flag)`` where ``model`` is of the
    corresponding class and ``flag`` is ``True`` if the model was just created
    and ``False`` otherwise.

    """
    instance = cls.q.filter_by(**kwargs).first()
    if instance:
      return instance, False
    instance = cls(**kwargs)
    if flush_if_new:
      instance.flush()
    return instance, True

  @declared_attr
  def __json__(cls):
    """Varnames that get JSONified.

    Doesn't emit any additional queries!

    """
    return list(
      varname
      for varname in dir(cls)
      if not varname.startswith('_')  # don't show private properties
      if (
        isinstance(getattr(cls, varname), property) 
      ) or (
        isinstance(getattr(cls, varname), InstrumentedAttribute) and
        isinstance(getattr(cls, varname).property, ColumnProperty)
      ) or (
        isinstance(getattr(cls, varname), InstrumentedAttribute) and
        isinstance(getattr(cls, varname).property, RelationshipProperty) and
        getattr(cls, varname).property.lazy in [False, 'joined', 'immediate']
      )
    )

  @declared_attr
  def __tablename__(cls):
    """Automatically create the table name.

    Override this to choose your own tablename (e.g. for single table
    inheritance).

    """
    return '%ss' % uncamelcase(cls.__name__)

  def __repr__(self):
    primary_keys = ', '.join(
      '%s=%r' % (k, getattr(self, k))
      for k, v in self.get_primary_key().items()
    )
    return '<%s (%s)>' % (self.__class__.__name__, primary_keys)

  def get_primary_key(self):
    """Returns the dictionary of primary keys for a given model.

    :rtype: dict

    """
    return dict(
      (k.name, getattr(self, k.name))
      for k in class_mapper(self.__class__).primary_key
    )

  def to_json(self, depth=1, expand=True):
    """Special implementation of to_json for Model objects.

    :param depth:
    :type depth: int
    :param expand: whether or not to repeat keys when jsonifying nested
      objects (defaults to ``True``). This is useful when the frontend
      has model support (e.g. using Backbone-Relational).
    :type expand: bool
    :rtype: dict

    The following attributes are included in the returned JSON:

    * all non private properties
    * all non private columns
    * all non private relationships which have their ``lazy`` attribute set to
      one of ``False, 'joined', 'immediate'``

    The consequence of this is that this method will never issue extra queries
    to populate the JSON. Furthermore, all the attribute names to be
    included are computed at class declaration so this method is very fast.

    """
    if depth <= self._json_depth:
      # this instance has already been jsonified at a greater or
      # equal depth, so we simply return its key
      return self.get_primary_key()
    if not expand:
      self._json_depth = depth
    rv = {}
    for varname in self.__json__:
      try:
        rv[varname] = to_json(getattr(self, varname), depth - 1)
      except ValueError as e:
        rv[varname] = e.message
    return rv

  def flush(self):
    session = self.q.session
    session.add(self)
    session.flush([self])

