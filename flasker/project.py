#!/usr/bin/env python

"""Project module."""

from celery.signals import task_postrun
from ConfigParser import SafeConfigParser
from flask import abort
from os.path import abspath, dirname, join, sep, split, splitext
from re import match, sub
from sqlalchemy import Column, create_engine  
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.declarative import declarative_base, declared_attr 
from sqlalchemy.orm import class_mapper, Query, scoped_session, sessionmaker
from sqlalchemy.orm.properties import RelationshipProperty
from weakref import proxy
from werkzeug.local import LocalProxy

from .util import Cacheable, convert, JSONEncodedDict, jsonify, Loggable, uncamelcase

class ProjectImportError(Exception):

  """Generic project import error.
  
  This will be raised for missing or invalid configuration files.
  
  """

  pass

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

  def __init__(self, db):
    self.db = db

  def __get__(self, obj, cls):
    try:
      mapper = class_mapper(cls)
      if mapper:
        return _BaseQuery(mapper, session=self.db.session())
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

# Main Project Class

class Project(object):

  """Project class.

  Global container for the Flask and Celery apps and SQLAlchemy database
  object.
  
  """

  __current__ = None

  config = {
    'PROJECT': {
      'NAME': '',
      'DOMAIN': '',
      'SUBDOMAIN': '',
      'MODULES': '',
      'DB_URL': 'sqlite://',
      'APP_FOLDER': 'app',
      'APP_STATIC_FOLDER': 'static',
      'APP_TEMPLATE_FOLDER': 'templates',
    },
    'APP': {
      'SECRET_KEY': 'a_default_unsafe_key',
    },
    'CELERY': {
      'BROKER_URL': 'redis://',
      'CELERY_RESULT_BACKEND': 'redis://',
      'CELERY_SEND_EVENTS': True
    }
  }

  def __init__(self, config_path):

    config = self._parse_config(config_path)
    for key in config:
      if key in self.config:
        self.config[key].update(config[key])
      else:
        self.config[key] = config[key]
    self._check_config()

    self.root_dir = dirname(abspath(config_path))
    self.domain = (
      self.config['PROJECT']['DOMAIN'] or
      sub(r'\W+', '_', self.config['PROJECT']['NAME'].lower())
    )
    self.subdomain = (
      self.config['PROJECT']['SUBDOMAIN'] or
      splitext(config_path)[0].replace(sep, '-')
    )

    assert Project.__current__ is None, 'More than one project.'
    Project.__current__ = proxy(self)

    self.app = None
    self.celery = None
    self._managers = []

  def __repr__(self):
    return '<Project %r, %r>' % (self.config['PROJECT']['NAME'], self.root_dir)

  def register_manager(self, manager, config_section=None):
    """Register a manager."""
    self._managers.append((manager, config_section))

  def make(self):
    """Create all project components.

    Note that the database connection isn't created here.
    
    """
    # core
    for mod in  ['app', 'celery']:
      __import__('flasker.core.%s' % mod)
    # project modules
    project_modules = self.config['PROJECT']['MODULES'].split(',') or []
    for mod in project_modules:
      __import__(mod.strip())
    # managers
    for manager, config_section in self._managers or []:
      if config_section:
        for k, v in self.config[config_section].items():
          manager.config[k] = v
      manager._before_register(self)
      self.app.register_blueprint(manager.blueprint)
      manager._after_register(self)

  def setup_database_connection(self, app=False, celery=False):
    """Initialize database connection."""
    engine = create_engine(
      self.config['PROJECT']['DB_URL'],
      pool_recycle=3600
    )
    Model.metadata.create_all(engine, checkfirst=True)
    self.session = scoped_session(sessionmaker(bind=engine))
    Model.query = _QueryProperty(self)
    if app:
      @self.app.teardown_request
      def teardown_request_handler(exception=None):
        self._dismantle_database_connections()
    if celery:
      @task_postrun.connect
      def task_postrun_handler(*args, **kwargs):
        self._dismantle_database_connections()

  def _dismantle_database_connections(self, **kwrds):
    """Remove database connection.

    Has to be called after app request/job terminates or connections
    will leak.

    """
    try:
      self.session.commit()
    except InvalidRequestError as e:
      self.session.rollback()
      self.session.expunge_all()
    finally:
      self.session.remove()

  def _parse_config(self, config_path):
    """Read the configuration file and return values as a dictionary.

    Raises ProjectImportError if no configuration file can be read at the
    file path entered.

    """
    parser = SafeConfigParser()
    parser.optionxform = str    # setting options to case-sensitive
    try:
      with open(config_path) as f:
        parser.readfp(f)
    except IOError as e:
      raise ProjectImportError(
        'Unable to parse configuration file at %s.' % config_path
      )
    return dict(
      (s, dict((k, convert(v)) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )

  def _check_config(self):
    """Make sure the configuration is valid.

    Any a priori configuration checks will go here.
    
    """
    conf = self.config
    # check that the project has a name
    if not conf['PROJECT']['NAME']:
      raise ProjectImportError('Missing project name.')

  @classmethod
  def get_current_project(cls):
    """Hook for ``current_project`` proxy."""
    return Project.__current__

current_project = LocalProxy(lambda: Project.get_current_project())

