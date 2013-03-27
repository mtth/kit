#!/usr/bin/env python

"""ORM Extension

This extension provides a customized SQLAlchemy model base and query.

Setup is straightforward:

.. code:: python

  from flasker import current_project as pj
  from flasker.ext import ORM

  orm = ORM(pj)

  Model = orm.Model                 # the customized base
  relationship = orm.relationship   # the customized relationship
  backref = orm.backref             # the associated backref

Models can now be created by subclassing ``orm.Model`` as follows:

.. code:: python

  from sqlalchemy import Column, ForeignKey, Integer, String

  class House(Model):

    id = Column(Integer, primary_key=True)
    address = Column(String(128))

  class Cat(Model):
      
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    house_id = Column(ForeignKey('houses.id'))

    house = relationship('House', backref=backref('cats', lazy='dynamic'))

Note that tablenames are automatically generated by default. For an
exhaustive list of all the properties and methods provided by ``orm.Model``
please refer to the documentation for :class:`flasker.ext.orm.BaseModel` below.

Models can be queried in several ways:

.. code:: python

  # the two following queries are equivalent
  query = pj.session.query(Cat)
  query = Cat.q

Both queries above are instances of :class:`flasker.ext.orm.Query`, which are
customized ``sqlalchemy.orm.Query`` objects (cf. below for the list of
available methods). If relationships (and backrefs) are defined using the
``orm.relationship`` and ``orm.backref`` functions, appender queries will
also return custom queries:

.. code:: python

  house = House.q.first()
  relationship_query = house.cats   # instance of flasker.ext.orm.Query

Finally, there is a special property ``c`` exposed on all children of
``orm.Model`` that returns an optimized count query (by default SQLAlchemy
count queries use subqueries which are very slow).  This is useful when
counting over large numbers of rows (10k and more), as the following benchmark
shows (~250k rows):

.. code:: python

  In [1]: %time Cat.q.count()
  CPU times: user 0.01 s, sys: 0.00 s, total: 0.01 s
  Wall time: 1.36 s
  Out[1]: 281992L

  In [2]: %time Cat.c.scalar()
  CPU times: user 0.00 s, sys: 0.00 s, total: 0.00 s
  Wall time: 0.06 s
  Out[2]: 281992L

"""

from functools import partial
from random import randint
from sqlalchemy import Column, func
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import (backref as _backref, class_mapper, Query as _Query,
  relationship as _relationship)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty

try:
  from pandas import DataFrame
except ImportError:
  pass

from ..util import (Cacheable, to_json, 
  JSONEncodedDict, Loggable, uncamelcase, query_to_dataframe, query_to_records)


class ORM(object):

  """The main ORM object.

  :param project: the project against which the extension will be registered
  :type project: flasker.project.Project
  :param create_all: whether or not to automatically create tables for the
    models defined (``True`` by default). Tables will only be created for
    models which do not have one already.
  :type create_all: bool

  When this object is initialized, it is responsible for adding the ``q`` and
  ``c`` query proxies on the model and configuring the project to use the
  custom :class:`flasker.ext.orm.Query` class.

  """

  def __init__(self, project, create_all=True):

    project.conf['SESSION']['QUERY_CLS'] = Query

    self.Model = declarative_base(cls=BaseModel)
    self.backref = partial(_backref, query_class=Query)
    self.relationship = partial(_relationship, query_class=Query)

    @project.run_after_module_imports
    def handler(project):
      self.Model.q = _QueryProperty(project)
      self.Model.c = _CountProperty(project)
      if create_all:
        self.Model.metadata.create_all(
          project.session.get_bind(),
          checkfirst=True
        )


class Query(_Query):

  """Base query class.

  All queries and relationships/backrefs defined using this extension will
  return an instance of this class.

  """

  def get_or_404(self, model_id):
    """Like get but aborts with 404 if not found.

    :param model_id: the model's primary key
    :type model_id: varies
    :rtype: model or HTTPError

    This method is from Flask-SQLAlchemy.
    
    """
    rv = self.get(model_id)
    if rv is None:
      abort(404)
    return rv

  def first_or_404(self):
    """Like first but aborts with 404 if not found.
    
    :rtype: model or HTTPError

    This method is from Flask-SQLAlchemy.
    
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

  def to_dataframe(self, lazy=True, **kwargs):
    """Loads a dataframe with the records from the query and returns it.

    :param lazy: whether or not to load the underlying objects. If set to
      ``False``, the dataframe will be populated with the contents of
      ``to_json`` of the models, otherwise it will only contain the columns
      existing in the database (default behavior). If lazy is ``True``, this
      method also accepts the same keyword arguments as
      :func:`flasker.util.query_to_dataframe`. For convenience, if no
      ``exclude`` kwarg is specified, it will default to ``['_cache']``.
    :type lazy: bool
    :rtype: pandas.DataFrame

    Requires the ``pandas`` library to be installed.

    """
    if lazy:
      kwargs.setdefault('exclude', ['_cache'])
      return query_to_dataframe(self, **kwargs)
    else:
      return DataFrame([model.to_json() for model in self])

  def to_records(self, **kwargs):
    """Raw execute of the query into a generator.

    :rtype: generator

    This method accepts the same keyword arguments as 
    :func:`flasker.util.query_to_records`.
    
    """
    return query_to_records(self, **kwargs)


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
        return Query(func.count(), session=session).select_from(cls)
    except UnmappedClassError:
      return None


class BaseModel(Cacheable, Loggable):

  """The custom SQLAlchemy base.

  Along with the methods described below, the following conveniences are
  provided:

  * Automatic table naming (to the model's class name uncamelcased with an
    extra s appended for good measure). To disable this behavior, simply
    override the ``__tablename__`` argument (setting it to ``None`` for
    single table inheritance).

  * Default implementation of ``__repr__`` with model class and primary keys

  * Caching (inherited from :class:`flasker.util.Cacheable`). The cache is
    persistent by default (``_cache`` is actually a
    :class:`flasker.util.JSONEncodedDict` column).

  * Logging (inherited from :class:`flasker.util.Loggable`)

  Recall that the ``q`` and ``c`` query properties are also available.

  """
  __json__ = None

  c = None
  q = None

  _cache = Column(JSONEncodedDict)
  _json_depth = 0

  @classmethod
  def __declare_last__(cls):
    """Varnames that get JSONified. Doesn't emit any additional queries!"""
    cls.__json__ = list(
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
      ) or (
        isinstance(getattr(cls, varname), AssociationProxy) and
        getattr(
          cls, getattr(cls, varname).target_collection
        ).property.lazy in [False, 'joined', 'immediate']
      )
    )

  @classmethod
  def _get_columns(cls, show_private=False):
    return {
      c.key: c
      for c in class_mapper(cls).columns
      if show_private or not c.key.startswith('_')
    }

  @classmethod
  def _get_related_models(cls, show_private=False):
    return {
      k: v.mapper.class_
      for k, v in cls._get_relationships(show_private).items()
    }

  @classmethod
  def _get_relationships(cls, show_private=False, lazy=None, uselist=None):
    return {
      rel.key: rel
      for rel in class_mapper(cls).relationships.values()
      if show_private or not rel.key.startswith('_')
      if lazy is None or rel.lazy in lazy
      if uselist is None or rel.uselist == uselist
    }

  @classmethod
  def _get_association_proxies(cls, show_private=False):
    return {
      varname: getattr(cls, varname)
      for varname in dir(cls)
      if isinstance(getattr(cls, varname), AssociationProxy)
      if show_private or not varname.startswith('_')
    }

  @classmethod
  def retrieve(cls, flush_if_new=True, **kwargs):
    """Given constructor arguments will return a match or create one.

    :param flush_if_new: whether or not to flush the model if created (this
      can be used to generate its ``id``).
    :type flush_if_new: bool
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
      instance._flush()
    return instance, True

  @declared_attr
  def __tablename__(cls):
    """Automatically create the table name."""
    return '%ss' % uncamelcase(cls.__name__)

  def __repr__(self):
    primary_keys = ', '.join(
      '%s=%r' % (k, getattr(self, k))
      for k, v in self.get_primary_key().items()
    )
    return '<%s (%s)>' % (self.__class__.__name__, primary_keys)

  def _flush(self):
    """Add the model to the session and flush."""
    session = self.q.session
    session.add(self)
    session.flush([self])

  def get_primary_key(self, as_tuple=False):
    """Returns a dictionary of primary keys for the given model.

    :param as_tuple: if set to ``True``, this method will return a tuple with
      the model's primary key values. Otherwise a dictionary is returned.
    :type as_tuple: bool
    :rtype: dict, tuple

    """
    if as_tuple:
      return tuple(
        getattr(self, k.name)
        for k in class_mapper(self.__class__).primary_key
      )
    else:
      return dict(
        (k.name, getattr(self, k.name))
        for k in class_mapper(self.__class__).primary_key
      )

  def to_json(self, depth=1, expand=True):
    """Serializes the model into a dictionary.

    :param depth:
    :type depth: int
    :param expand: whether or not to repeat keys when jsonifying nested
      objects (defaults to ``True``). This is useful when the frontend
      has model support (e.g. using Backbone-Relational).
    :type expand: bool
    :rtype: dict

    The following attributes are included in the returned JSON:

    * all non private columns
    * all non private properties
    * all non private relationships which have their ``lazy`` attribute set to
      one of ``False, 'joined', 'immediate'``

    A consequence of this is that this method will never issue extra queries
    to populate the JSON. Furthermore, all the attribute names to be
    included are computed at class declaration so this method is very fast.

    .. note::

      To change which attributes are included in the dictionary, you can 
      override the ``__json__`` attribute.

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

