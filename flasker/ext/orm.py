#!/usr/bin/env python

from random import randint
from sqlalchemy import Column, func
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import class_mapper, Query as _Query
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty

from ..util import (Cacheable, _jsonify, JSONDepthExceededError,
  JSONEncodedDict, Loggable, uncamelcase, query_to_dataframe)


class ORM(object):

  config = {
    'CREATE_ALL': True
  }

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      self.config[k.upper()] = v

  def on_register(self, project):
    project._query_class = Query

    @project.before_startup
    def handler(project):
      if self.config['CREATE_ALL']:
        Model.metadata.create_all(project._engine, checkfirst=True)
      Model.q = _QueryProperty(project)
      Model.c = _CountProperty(project)


class Query(_Query):

  """Base query class.

  The first two methods are from Flask-SQLAlchemy.

  """

  def get_or_404(self, model_id):
    """Like get but aborts with 404 if not found."""
    rv = self.get(model_id)
    if rv is None:
      abort(404)
    return rv

  def first_or_404(self):
    """Like first but aborts with 404 if not found."""
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

  def dataframe(self, *args, **kwargs):
    """Loads a dataframe with the records from the query and returns it.

    Accepts the same arguments as ``flasker.util.query_to_dataframe``.
    Requires the ``pandas`` library to be installed.

    """
    return query_to_dataframe(self, *args, **kwargs)


class _QueryProperty(object):

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

  """Adding a few features to the declarative base.

  Currently:

  * Automatic table naming
  * Caching
  * Jsonifying
  * Logging

  """

  _cache = Column(JSONEncodedDict)
  _json_depth = 0

  c = None
  q = None

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      setattr(self, k, v)

  def __repr__(self):
    primary_keys = ', '.join(
      '%s=%r' % (k, getattr(self, k))
      for k in self.__class__.get_primary_key_names()
    )
    return '<%s (%s)>' % (self.__class__.__name__, primary_keys)

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

  def __init__(self, **kwargs):
    for k, v in kwargs.items():
      setattr(self, k, v)

  def __repr__(self):
    primary_keys = ', '.join(
      '%s=%r' % (k, v)
      for k, v in self.get_primary_keys().items()
    )
    return '<%s (%s)>' % (self.__class__.__name__, primary_keys)

  def jsonify(self, depth=1, expand=True):
    """Special implementation of jsonify for Model objects.
    
    Overrides the basic jsonify method to specialize it for models.

    This function minimizes the number of lookups it does (no dynamic
    type checking on the properties for example) to maximize speed.

    :param depth:
    :type depth: int
    :rtype: dict

    """
    if depth <= self._json_depth:
      # this instance has already been jsonified at a greater or
      # equal depth, so we simply return its key (only used if expand is False)
      return self.get_primary_keys()
    if not expand:
      self._json_depth = depth
    rv = {}
    for varname in self.__json__:
      try:
        rv[varname] = _jsonify(getattr(self, varname), depth - 1, expand)
      except ValueError as e:
        rv[varname] = e.message
      except JSONDepthExceededError:
        pass
    return rv

  def get_primary_keys(self):
    return dict(
      (k.name, getattr(self, k.name))
      for k in self.__class__._primary_keys()
    )

  @classmethod
  def find_or_create(cls, **kwargs):
    instance = self.filter_by(**kwargs).first()
    if instance:
      return instance, False
    instance = cls(**kwargs)
    session = cls.q.db.session
    session.add(instance)
    session.flush()
    return instance, True

  @classmethod
  def _columns(cls, show_private=False):
    columns = class_mapper(cls).columns
    if not show_private:
      columns = [c for c in columns if not c.key.startswith('_')]
    return columns

  @classmethod
  def _primary_keys(cls):
    return class_mapper(cls).primary_key

  @classmethod
  def _related_models(cls, show_private=False):
    return [
      (r.key, r.mapper.class_)
      for r in cls._relationships(show_private)
    ]

  @classmethod
  def _relationships(cls, show_private=False):
    rels =  class_mapper(cls).relationships.values()
    if not show_private:
      rels = [rel for rel in rels if not rel.key.startswith('_')]
    return rels

Model = declarative_base(cls=Base)

