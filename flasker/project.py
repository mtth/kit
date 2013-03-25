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
from werkzeug.local import LocalProxy

from .core import make_celery_app, make_flask_app
from .util import convert


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
      'NAME':             '',
      'MODULES':          '',
    },
    'ENGINE': {
      'URL':              'sqlite://',
      'AUTOCOMMIT':       True,
    },
    'FLASK': {
      'ROOT_FOLDER':      'app',
      'STATIC_FOLDER':    'static',
      'TEMPLATE_FOLDER':  'templates',
    },
    'CELERY': {
    },
  }

  query_class = Query

  _flask = None
  _celery = None
  _path = None

  __state = {}

  def __init__(self, config_path=None):

    self.__dict__ = self.__state

    if config_path is None:

      if self._path is None:
        raise ProjectImportError('Project instantiation outside the Flasker '
                                 'command line tool requires a '
                                 'configuration file path.')

    else:

      if self._path and config_path != self._path:
        raise ProjectImportError('Cannot instantiante projects for different '
                                 'configuration files in the same process.')

      elif not self._path:
        self._path = abspath(config_path)
        self.config = self._parse_config(config_path)
        self._load_project_modules()
        self.session, self._engine = self._make_session()
        for func in self._before_startup:
          func(self)

  def __repr__(self):
    return '<Project %r>' % (self.config['PROJECT']['NAME'], )

  @property
  def flask(self):
    if self._flask is None:
      self._flask = make_flask_app(self)
    return self._flask

  @property
  def celery(self):
    if self._celery is None:
      self._celery = make_celery_app(self)
    return self._celery

  def before_startup(self, func):
    """Hook to run a function right before project starts.

    :param func: the function to be called right before startup. It will be
      passed the project as single argument.
    :type func: callable

    This decorator can be used to run functions after all the components of
    the project have been created.
    
    """
    self._before_startup.append(func)

  def _load_project_modules(self):
    """Create all project components."""
    self._before_startup = []
    path.append(self.config['PROJECT']['ROOT_DIR'])
    project_modules = self.config['PROJECT']['MODULES'].split(',') or []
    for mod in project_modules:
      __import__(mod.strip())

  def _make_session(self):
    """Setup the database engine."""
    engine_ops = dict((k.lower(), v) for k,v in self.config['ENGINE'].items())
    engine_ops.pop('autocommit')
    engine = create_engine(engine_ops.pop('url'), **engine_ops)
    session = scoped_session(
      sessionmaker(bind=engine, query_cls=self.query_class)
    )
    return session, engine

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
    """Read the configuration file and return values as a dictionary."""
    parser = SafeConfigParser()
    parser.optionxform = str    # setting options to case-sensitive

    try:
      with open(config_path) as f:
        parser.readfp(f)
    except IOError as e:
      raise ProjectImportError(
        'Unable to parse configuration file at %s.' % config_path
      )
    else:
      conf = {
        s: {k: convert(v, allow_json=True) for (k, v) in parser.items(s)}
        for s in parser.sections()
      }

    config = self.config.copy()
    for key in conf:
      if key in self.config:
        config[key].update(conf[key])
      else:
        config[key] = conf[key]

    if not config['PROJECT']['NAME']:
      raise ProjectImportError('Missing project name.')

    config['PROJECT'].setdefault('ROOT_DIR', dirname(self._path))
    config['CELERY'].setdefault(
      'DOMAIN', 
      sub(r'\W+', '_', self.config['PROJECT']['NAME'].lower())
    )
    config['CELERY'].setdefault(
      'SUBDOMAIN', 
      splitext(config_path)[0].replace(sep, '-')
    )

    return config

#: Proxy to the current project
current_project = LocalProxy(Project)

