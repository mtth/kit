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

from __future__ import absolute_import

from collections import defaultdict
from os.path import abspath, dirname, join, sep, split, splitext
from re import match, sub
from sqlalchemy import create_engine  
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import scoped_session, sessionmaker
from sys import path
from werkzeug.local import LocalProxy

from .util import parse_config


class ProjectImportError(Exception):

  pass


class Project(object):

  """Project class.

  :param conf_path: path to the configuration file. The following sections
    are special: ``PROJECT``, ``ENGINE``, ``FLASK``, ``CELERY``. All but 
    ``PROJECT`` are optional. See below for a list of available options in each
    section.
  :type conf_path: str

  The following options are available each section of the configuration file
  (as a convenience, parameters stored as JSON strings are also accepted,
  which can be useful for example to configure Celery queues):

  * ``PROJECT``

    * ``MODULES``: comma separated list of the project's modules. They must be
      importable from the configuration file's folder.
    * ``DISABLE_FLASK``
    * ``DISABLE_CELERY``

  * ``ENGINE``

    * ``URL``: the url to the database
    * any valid arguments to ``sqlalchemy.create_engine``

  * ``SESSION``

    * ``SMARTCOMMIT``: if ``True`` (default), all database transactions
      will be committed after each Flask app request and Celery task
      completion. If ``False`` the session will simply be removed.
    * any valid arguments to ``sqlalchemy.orm.session_maker``

  * ``FLASK``

    * ``ROOT_FOLDER``: path to the Flask application's root folder
      relative to the configuration file (defaults to ``app``).
    * ``STATIC_FOLDER``: the application's ``static_folder`` relative to
      the application's root folder (defaults to ``static``).
    * ``TEMPLATE_FOLDER``: the application's ``template_folder`` relative
      to the application's root folder (defaults to ``templates``).
    * any valid Flask configuration option

  * ``CELERY``

    * ``MAIN`` 
    * any valid Celery configuration option
  
  """

  #: Default configuration
  default_conf = {
    'PROJECT': {
      'MODULES':          '',
      'DISABLE_FLASK':    False,
      'DISABLE_CELERY':   False,
    },
    'ENGINE': {
      'URL':              'sqlite://',
    },
    'SESSION': {
      'SMARTCOMMIT':      True,
    },
    'FLASK': {
      'NAME':             'app',
      'ROOT_FOLDER':      'app',
      'STATIC_FOLDER':    'static',
      'TEMPLATE_FOLDER':  'templates',
    },
    'CELERY': {
      'MAIN':             '__main__',
    },
  }

  #: Dictionary of configuration values
  conf = None

  #: Path to current configuration file
  conf_path = None

  _flask = None
  _celery = None
  _session = None

  __state = {}

  def __init__(self, conf_path=None):

    self.__dict__ = self.__state

    if conf_path is None:

      if not self.conf_path:
        raise ProjectImportError('Project instantiation outside the Flasker '
                                 'command line tool requires a '
                                 'configuration file path.')

    else:

      if self.conf_path and conf_path != self.conf_path:
        raise ProjectImportError('Cannot instantiante projects for different '
                                 'configuration files in the same process.')

      elif not self.conf_path:

        # load configuration
        self.conf = parse_config(
          conf_path,
          default=self.default_conf,
          case_sensitive=True
        )
        self.conf_path = abspath(conf_path)

        # load all project modules
        self._funcs = []
        path.append(dirname(self.conf_path))
        project_modules = self.conf['PROJECT']['MODULES'].split(',')
        for mod in project_modules:
          __import__(mod.strip())
        for func in self._funcs:
          func(self)

  def __repr__(self):
    return '<Project %r>' % (self.conf_path, )

  @property
  def flask(self):
    """Flask application.

    Lazily initialized.

    """
    if self._flask is None and not self.conf['PROJECT']['DISABLE_FLASK']:

      from flask import Flask

      flask_app = Flask(
        self.conf['FLASK']['NAME'],
        static_folder=self.conf['FLASK']['STATIC_FOLDER'],
        template_folder=self.conf['FLASK']['TEMPLATE_FOLDER'],
        instance_path=join(
          dirname(self.conf_path),
          self.conf['FLASK']['ROOT_FOLDER'],
        ),
        instance_relative_config=True,
      )

      flask_app.config.update({
        k: v
        for k, v in self.conf['FLASK'].items()
        if not k in self.default_conf['FLASK']
      })

      @flask_app.teardown_request
      def teardown_request_handler(exception=None):
        self._remove_session()

      self._flask = flask_app
    return self._flask

  @property
  def celery(self):
    """Celery application.

    Lazily initialized.

    """
    if self._celery is None and not self.conf['PROJECT']['DISABLE_CELERY']:

      from celery import Celery
      from celery.signals import task_postrun, worker_process_init
      from celery.task import periodic_task

      celery_app = Celery(self.conf['CELERY']['MAIN'])

      celery_app.conf.update({
        k: v
        for k, v in self.conf['CELERY'].items()
        if not k in self.default_conf['CELERY']
      })

      # proxy for easy access
      celery_app.periodic_task = periodic_task

      # maybe not required with lazy session initialization
      # TODO: check this
      # @worker_process_init.connect
      # def create_worker_connection(*args, **kwargs):
      #   self._create_session()

      @task_postrun.connect
      def task_postrun_handler(*args, **kwargs):
        self._remove_session()

      self._celery = celery_app
    return self._celery

  @property
  def session(self):
    """SQLAlchemy scoped sessionmaker.

    Lazily initialized.

    """
    if self._session is None:
      engine = create_engine(
        self.conf['ENGINE']['URL'],
        **{
          k.lower(): v 
          for k, v in self.conf['ENGINE'].items()
          if not k in self.default_conf['ENGINE']
        }
      )
      session = scoped_session(
        sessionmaker(
          bind=engine,
          **{
            k.lower(): v
            for k, v in self.conf['SESSION'].items()
            if not k in self.default_conf['SESSION']
          }
        )
      )

      self._session = session
    return self._session

  def run_after_module_imports(self, func):
    """Hook to run a function right after all project modules are imported.

    :param func: the function to be called right before startup. It will be
      passed the project as single argument.
    :type func: callable

    This decorator can be used to run functions after all the components of
    the project have been created.
    
    """
    self._funcs.append(func)

  def _remove_session(self):
    """Remove database connections."""
    try:
      if self.conf['SESSION']['SMARTCOMMIT']:
        self.session.commit()
    except InvalidRequestError as e:
      self.session.rollback()
      self.session.expunge_all()
      raise e
    finally:
      self.session.remove()

  def _reset(self):
    """Reset current project."""
    self.__class__.__state = {}


#: Proxy to the current project
current_project = LocalProxy(Project)

