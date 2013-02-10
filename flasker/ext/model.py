#!/usr/bin/env python

from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import class_mapper, Query
from sqlalchemy.orm.properties import RelationshipProperty

from ..project import current_project as pj
from ..util import Cacheable, JSONEncodedDict, jsonify, Loggable, uncamelcase

# SQLAlchemy setup

class _BaseQuery(Query):

  """Base query class.

  From Flask-SQLAlchemy.

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

class _QueryProperty(object):

  def __init__(self, project):
    self.project = project

  def __get__(self, obj, cls):
    try:
      mapper = class_mapper(cls)
      if mapper:
        return _BaseQuery(mapper, session=self.project.session())
    except UnmappedClassError:
      return None

class ExpandedBase(Cacheable, Loggable):

  """Adding a few features to the declarative base.

  Currently:

  * Automatic table naming
  * Caching
  * Jsonifying
  * Logging

  """

  _cache = Column(JSONEncodedDict)
  _json_depth = -1

  json_exclude = None
  json_include = None
  query = None

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
  def __tablename__(cls):
    """Automatically create the table name.

    Override this to choose your own tablename (e.g. for single table
    inheritance).

    """
    return '%ss' % uncamelcase(cls.__name__)

  @declared_attr
  def _json_attributes(cls):
    """Create the dictionary of attributes that will be JSONified.

    This is only run once, on class initialization, which makes jsonify calls
    much faster.

    By default, includes all public (don't start with _):

    * properties
    * columns that aren't foreignkeys.
    * joined relationships (where lazy is False)

    """
    rv = set(
        varname for varname in dir(cls)
        if not varname.startswith('_')  # don't show private properties
        if (
          isinstance(getattr(cls, varname), property) 
        ) or (
          isinstance(getattr(cls, varname), Column) and
          not getattr(cls, varname).foreign_keys
        ) or (
          isinstance(getattr(cls, varname), RelationshipProperty) and
          not getattr(cls, varname).lazy == 'dynamic'
        )
      )
    if cls.json_include:
      rv = rv | set(cls.json_include)
    if cls.json_exclude:
      rv = rv - set(cls.json_exclude)
    return list(rv)

  def jsonify(self, depth=0):
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
      # equal depth, so we simply return its key
      return self.get_primary_keys()
    rv = {}
    self._json_depth = depth
    for varname in self._json_attributes:
      try:
        rv[varname] = jsonify(getattr(self, varname), depth)
      except ValueError as e:
        rv[varname] = e.message
    return rv

  def get_primary_keys(self):
    return dict(
      (k, getattr(self, k))
      for k in self.__class__.get_primary_key_names()
    )

  @classmethod
  def find_or_create(cls, **kwargs):
    instance = self.filter_by(**kwargs).first()
    if instance:
      return instance, False
    instance = cls(**kwargs)
    session = cls.query.db.session
    session.add(instance)
    session.flush()
    return instance, True

  @classmethod
  def get_columns(cls, show_private=False):
    columns = class_mapper(cls).columns
    if not show_private:
      columns = [c for c in columns if not c.key.startswith('_')]
    return columns

  @classmethod
  def get_relationships(cls):
    return class_mapper(cls).relationships

  @classmethod
  def get_related_models(cls):
    return [(k, v.mapper.class_) for k, v in cls.get_relationships().items()]

  @classmethod
  def get_primary_key_names(cls):
    return [key.name for key in class_mapper(cls).primary_key]

Model = declarative_base(cls=ExpandedBase)

@pj.before_startup
def before_startup(project):
  Model.metadata.create_all(project._engine, checkfirst=True)
  Model.query = _QueryProperty(project)

