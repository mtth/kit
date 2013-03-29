#!/usr/bin/env python

"""SQAlchemy helpers."""

from __future__ import absolute_import

from json import dumps, loads
from random import randint
from sqlalchemy import Column, func
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.ext.declarative import declared_attr 
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import class_mapper, Query as _Query
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.types import TypeDecorator, UnicodeText
from sqlalchemy.orm.properties import ColumnProperty, RelationshipProperty

try:
  from pandas import DataFrame
except ImportError:
  pass

from .helpers import uncamelcase, to_json
from .mixins import Cacheable, Loggable


# Base model

class Model(Cacheable, Loggable):

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

  """

  @classmethod
  def __declare_last__(cls):
    """Creates the ``__json__`` attribute.
    
    Varnames that get JSONified. Doesn't emit any additional queries!

    TODO: use _get_columns and other methods to generate thist list.

    """
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
  def retrieve(cls, from_key=False, if_not_found='pass', **kwargs):
    """Given constructor arguments will return a match or create one.

    :param if_not_found: whether or not to create and flush the model if 
      created (this can be used to generate its ``id``). Acceptable values:
      'flush' (create and flush), 'create' (only create), 'pass' (do nothing).
    :type if_not_found: str
    :param from_key: instead of issuing a filter on kwargs, this will issue
      a get query by id using this parameter. Note that in this case, any other
      keyword arguments will only be used if a new instance is created.
    :type from_key: bool
    :param kwargs: constructor arguments
    :rtype: tuple

    This method returns a tuple ``(model, flag)`` where ``model`` is of the
    corresponding class and ``flag`` is ``True`` if the model was just created
    and ``False`` otherwise.

    """
    if from_key:
      model_primary_key = tuple(
        kwargs[k.name]
        for k in class_mapper(cls).primary_key
      )
      instance = cls.q.get(model_primary_key)
    else:
      instance = cls.q.filter_by(**kwargs).first()
    if if_not_found == 'pass':
      return instance
    else:
      if instance:
        return instance, False
      else:
        instance = cls(**kwargs)
        if if_not_found == 'flush':
          instance.flush()
      return instance, True

  def __repr__(self):
    primary_keys = ', '.join(
      '%s=%r' % (k, getattr(self, k))
      for k, v in self.get_primary_key().items()
    )
    return '<%s (%s)>' % (self.__class__.__name__, primary_keys)

  @declared_attr
  def __tablename__(cls):
    """Automatically create the table name."""
    return '%ss' % uncamelcase(cls.__name__)

  @declared_attr
  def _cache(cls):
    """Automatically create the table name."""
    return Column(JSONEncodedDict)

  def flush(self, merge=False):
    """Add the model to the session and flush.
    
    :param merge: if ``True``, will merge instead of add.
    :type merge: bool
    
    """
    session = self.q.session
    if merge:
      session.merge(self)
    else:
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

  def to_json(self, depth=1):
    """Serializes the model into a dictionary.

    :param depth:
    :type depth: int
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
    if depth <= 0:
      return self.get_primary_key()
    rv = {}
    for varname in self.__json__:
      try:
        rv[varname] = to_json(getattr(self, varname), depth - 1)
      except ValueError as e:
        rv[varname] = e.message
    return rv


# Query helpers

def query_to_models(query):
  """Returns the model classes associated with a query.
  
  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :rtype: list

  """
  if hasattr(query, 'attr'):
    # this is a subquery
    return [query.attr.target_mapper]
  else:
    # this is a main query
    return [
      d['expr'].class_
      for d in query.column_descriptions
      if isinstance(d['expr'], Mapper)
    ]

def query_to_dataframe(query, connection=None, exclude=None, index=None,
                       columns=None, coerce_float=False):
  """Load a Pandas dataframe from an SQLAlchemy query.

  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :param connection: the connection to use to execute the query. By default
    the method will create a new connection using the session's bound engine
    and properly close it afterwards.
  :type connection: sqlalchemy.engine.base.Connection
  :param exclude: a list of column names to exclude from the dataframe
  :type exclude: list
  :param index: the column to use as index
  :type index: str
  :param names: a list of column names. If unspecified, the method will use
    the table's keys from the query's metadata. If the passed data do not have
    named associated with them, this argument provides names for the columns.
    Otherwise this argument indicates the order of the columns in the result
    (any names not found in the data will become all-NA columns)
  :type names: list
  :param coerce_float: Attempt to convert values to non-string, non-numeric
    objects (like decimal.Decimal) to floating point.
  :type coerce_float: bool
  :rtype: pandas.DataFrame
  
  """
  connection = connection or query.session.get_bind()
  exclude = exclude or []
  result = connection.execute(query.statement)
  columns = columns or result.keys()
  dataframe = DataFrame.from_records(
    result.fetchall(),
    columns=columns,
    exclude=exclude,
    index=index,
    coerce_float=coerce_float,
  )
  result.close()
  return dataframe

def query_to_records(query, connection=None):
  """Raw execute of the query into a generator.

  :param query: the query to be executed
  :type query: sqlalchemy.orm.query.Query
  :param connection: the connection to use to execute the query. By default
    the method will create a new connection using the session's bound engine
    and properly close it afterwards.
  :type connection: sqlalchemy.engine.base.Connection
  :rtype: generator

  About 5 times faster than loading the objects. Useful if only interested in
  raw columns of the model::

    # for ~300k models
    In [1]: %time [m.id for s in Model.q]
    CPU times: user 48.22 s, sys: 2.62 s, total: 50.84 s
    Wall time: 52.19 s
    In [2]: %time [m['id'] for s in query_to_records(Model.q)]
    CPU times: user 9.12 s, sys: 0.20 s, total: 9.32 s
    Wall time: 10.32 s
  
  """
  connection = connection or query.session.get_bind()
  result = connection.execute(query.statement)
  keys = result.keys()
  for record in result:
    yield {k:v for k, v in zip(keys, record)}
  result.close()


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

  def fast_count(self):
    """Fast counting, bypassing subqueries.

    By default SQLAlchemy count queries use subqueries (which are very slow
    on MySQL). This method is useful when counting over large numbers of rows
    (10k and more), as the following benchmark shows (~250k rows):

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
    models = query_to_models(self)
    if len(models) != 1:
      # initial query is over more than one model
      # not clear how to implement the count in that case
      raise ValueError('Fast count unavailable for this query.')
    count_query = Query(func.count(), session=self.session)
    count_query = count_query.select_from(models[0])
    count_query._criterion = self._criterion
    return count_query.scalar()

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
      return query_to_dataframe(
        self,
        connection=self._connection_from_session(),
        **kwargs
      )
    else:
      return DataFrame([model.to_json() for model in self])

  def to_records(self, **kwargs):
    """Raw execute of the query into a generator.

    :rtype: generator

    This method accepts the same keyword arguments as 
    :func:`flasker.util.query_to_records`.
    
    """
    return query_to_records(
      self,
      connection=self._connection_from_session(),
      **kwargs
    )


# Mutables

class _JSONEncodedType(TypeDecorator):

  """Base class for storing python mutables as a JSON.

  For mutability tracking, associate with a Mutable.

  The underlying immutable object is of kind ``sqlalchemy.types.unicodetext``.
  Note that it has a character limit so care is needed when storing very large
  objects.


  """

  impl = UnicodeText

  def process_bind_param(self, value, dialect):
    return dumps(value) if value else None

  def process_result_value(self, value, dialect):
    raise NotImplementedError()


class JSONEncodedDict(_JSONEncodedType):

  """Implements dictionary column field type for SQLAlchemy.

  This can be used as a Column type during table creation::

    some_column_name = Column(JSONEncodedDict)

  It also implements limited  mutability tracking to know when to update the
  database: set, del and update actions are tracked. If another method to
  update the dictionary is used, it will not automatically flag the
  dictionary for update (for example if a deeply nested key is updated).
  In such a case, the ``changed`` method needs the be called manually
  after the operation.

  """

  def process_result_value(self, value, dialect):
    return loads(value) if value else {}


class _MutableDict(Mutable, dict):

  """Used with JSONEncoded dict to be able to track updates.

  This enables the database to know when it should update the stored string
  representation of the dictionary. This is much more efficient than naive
  automatic updating after each query.

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
    
_MutableDict.associate_with(JSONEncodedDict)


class JSONEncodedList(_JSONEncodedType):

  """Implements list column field type for SQLAlchemy.

  This can be used as a Column type during table creation::

    some_column_name = Column(JSONEncodedList)

  Currently only set, delete, append and extend events are tracked. Others
  will require a call to ``changed`` to be persisted.

  """

  def process_result_value(self, value, dialect):
    return loads(value) if value else []


class _MutableList(Mutable, list):

  """Used with JSONEncoded list to be able to track updates.

  This enables the database to know when it should update the stored string
  representation of the dictionary. This is much more efficient than naive
  automatic updating after each query.

  """

  @classmethod
  def coerce(cls, key, value):
    """Convert plain dictionaries to Features."""
    if not isinstance(value, cls):
      if isinstance(value, list):
        return cls(value)
      return Mutable.coerce(key, value) # this will raise an error
    else:
      return value

  def append(self, *args, **kwargs):
    """Detect update events and emit change events."""
    list.append(self, *args, **kwargs)
    self.changed()

  def extend(self, *args, **kwargs):
    """Detect update events and emit change events."""
    list.extend(self, *args, **kwargs)
    self.changed()
    
  def __setitem__(self, index, value):
    """Detect set events and emit change events."""
    list.__setitem__(self, index, value)
    self.changed()
    
  def __delitem__(self, index):
    """Detect del events and emit change events."""
    list.__delitem__(self, index)
    self.changed()

_MutableList.associate_with(JSONEncodedList)

