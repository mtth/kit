#!/usr/bin/env python

"""Project module.

This module defines:

* the :class:`flasker.project.Project` class which contains
  all the logic between the Flask and Celery applications and the SQLAlchemy
  sessions.

* the ``current_project`` proxy

For convenience, both these variables are also available directly in the
``flasker`` namespace.

.. note::

  In most cases :class:`flasker.project.Project` will not need to be
  instantiated explicitely (the console tool handles the setup) and will only
  be accessed via the ``current_project`` proxy. In some cases however the
  constructor can be called to create a project (for example from an IPython
  notebook or to use a separate WSGI server).

  .. code:: python

    from flasker import Project

    # instantiating the project
    pj = Project('path/to/config.cfg')

    # the application that would be passed to a WSGI server
    application = pj.flask

"""

from ConfigParser import SafeConfigParser
from os.path import abspath, dirname, join, sep, split, splitext
from re import match, sub
from sqlalchemy import create_engine  
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Query, scoped_session, sessionmaker
from sys import path
from threading import local
from werkzeug.local import LocalProxy

from .util import convert


class _LocalStorage(local):

  """Thread local storage."""
  
  _current_project = None

_local_storage = _LocalStorage()


class ProjectImportError(Exception):

  pass


class Project(object):

  """Project class.

  :param config_path: path to the configuration file. The following sections
    are special: ``PROJECT``, ``ENGINE``, ``FLASK``, ``CELERY``. All but 
    ``PROJECT`` are optional. See below for a list of available options in each
    section.  :type config_path: str
  :param make: whether or not to create all the project components. This should
    always be true, except in some cases where it is useful to check
    consistency of the configuration before doing so. ``_make`` should then be
    called manually after these checks are done.
  :type make: bool

  The following options are available each section of the configuration file
  (as a convenience, parameters stored as JSON strings are also accepted,
  which can be useful for example to configure Celery queues):

  * ``PROJECT``

    * ``NAME``: the name of the project, used for debugging and to generate a
      default domain name for the Celery workers.
    * ``MODULES``: comma separated list of the project's modules. They must be
      importable from the configuration file's folder.

  * ``ENGINE``

    * ``URL``: the url to the database
    * ``AUTOCOMMIT``: if ``True`` (default), all database transactions
      will be committed after each Flask app request and Celery task
      completion. If ``False`` the session will simply be removed.
    * any valid arguments to ``sqlalchemy.create_engine``

  * ``FLASK``

    * ``ROOT_FOLDER``: path to the Flask application's root folder
      relative to the configuration file (defaults to ``app``).
    * ``STATIC_FOLDER``: the application's ``static_folder`` relative to
      the application's root folder (defaults to ``static``).
    * ``TEMPLATE_FOLDER``: the application's ``template_folder`` relative
      to the application's root folder (defaults to ``templates``).
    * any valid Flask configuration option

  * ``CELERY``

    * ``DOMAIN``: if specified, used to generate Celery worker hostnames
      (defaults to the project name, sluggified).
    * ``SUBDOMAIN``: if specified, used to generate Celery worker hostnames 
      (defaults to the configuration file's name).
    * any valid Celery configuration option
  
  """

  config = {
    'PROJECT': {
      'NAME':                   '',
      'MODULES':                '',
    },
    'ENGINE': {
      'URL':                    'sqlite://',
      'AUTOCOMMIT':             True,
    },
    'FLASK': {
      'ROOT_FOLDER':            'app',
      'STATIC_FOLDER':          'static',
      'TEMPLATE_FOLDER':        'templates',
    },
    'CELERY': {
      'DOMAIN':                 '',
      'SUBDOMAIN':              '',
    },
  }

  config_path = None

  flask = None
  celery = None
  session = None

  _current = None
  _before_startup = None
  _engine = None
  _query_class = Query

  __state = {}

  def __init__(self, config_path=None, make=True):

    self.__dict__ = self.__state

    if self.__class__._current:

      if config_path and config_path != self.config_path:
        raise ProjectImportError('Cannot instantiante projects for different '
                                 'configuration files in the same process.')

    else:

      if config_path is None:
        if self.config_path is None:
          raise ProjectImportError('Project instantiation outside the Flasker '
                                   'command line tool requires a '
                                   'configuration file path.')
        config_path = self.config_path
      else:
        self.__class__.config_path = config_path

      config = self._parse_config(config_path)
      for key in config:
        if key in self.config:
          self.config[key].update(config[key])
        else:
          self.config[key] = config[key]

      self.root_dir = dirname(abspath(config_path))
      self.domain = (
        self.config['CELERY']['DOMAIN'] or
        sub(r'\W+', '_', self.config['PROJECT']['NAME'].lower())
      )
      self.subdomain = (
        self.config['CELERY']['SUBDOMAIN'] or
        splitext(config_path)[0].replace(sep, '-')
      )

      path.append(self.root_dir)

      self.__class__._current = self
      self._before_startup = []

      if make:
        self._make()

  def __repr__(self):
    return '<Project %r, %r>' % (
      self.config['PROJECT']['NAME'], self.config_path
    )

  def before_startup(self, func):
    """Hook to run a function right before project starts.

    :param func: the function to be called right before startup. It will be
      passed the project as single argument.
    :type func: callable

    This decorator can be used to run functions after all the components of
    the project have been created.
    
    """
    self._before_startup.append(func)

  def _make(self):
    """Create all project components."""

    # core
    for mod in  ['flask', 'celery']:
      __import__('flasker.core.%s' % mod)

    # project modules
    project_modules = self.config['PROJECT']['MODULES'].split(',') or []
    for mod in project_modules:
      __import__(mod.strip())

    # database
    self._setup_database_connection()

    # final hook
    for func in self._before_startup or []:
      func(self)

  def _setup_database_connection(self):
    """Setup the database engine."""
    engine_ops = dict((k.lower(), v) for k,v in self.config['ENGINE'].items())
    engine_ops.pop('autocommit')
    self.__class__._engine = create_engine(engine_ops.pop('url'), **engine_ops)
    self.__class__.session = scoped_session(
      sessionmaker(bind=self._engine, query_cls=self._query_class)
    )

  def _dismantle_database_connections(self):
    """Remove database connections."""
    try:
      if self.config['ENGINE']['AUTOCOMMIT']:
        self.session.commit()
    except InvalidRequestError as e:
      self.session.rollback()
      self.session.expunge_all()
      raise e
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
    conf = dict(
      (s, dict((k, convert(v, allow_json=True)) for (k, v) in parser.items(s)))
      for s in parser.sections()
    )
    if not conf['PROJECT']['NAME']:
      raise ProjectImportError('Missing project name.')
    return conf


def _get_current_project():
  return Project._current or Project()

#: Proxy to the current project
current_project = LocalProxy(_get_current_project)

