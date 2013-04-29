#!/usr/bin/env python

"""

Quickstart
==========

Configuration options
---------------------

The following configuration file demonstrates all the options available in a
kit configuration file:

.. code:: yaml

  root: '.'
  modules: []
  flasks:
    - modules: ['app']
      kwargs:
        static_folder: 'st'
      config:
        debug: yes
  celeries:
    - modules: ['tasks']
      config:
        broker_url: 'redis://'
  sessions:
    db:
      url: 'sqlite://'
      options:
        commit: yes
        raise: no
      engine:
        echo: yes


  * ``root``: project root, will be added to your python path. Useful if your
    configuration files are in a subdirectory of your project.

  * ``modules``: list of modules to import (and that don't belong to an
    application).

  * ``flasks``: list of Flask application settings. Each item has the following
    keys available:

    * ``modules``: list of modules where this application is used. Inside each
      of these modules, you can use :func:`kit.Flask` to recover this
      configured application. The application's name will be automatically
      generated from this list of modules.
    * ``kwargs``: dctionary of keyword arguments passed to the
      :class:`flask.Flask` constructor.
    * ``config``: dicionary of configuration options used to configure the
      application. Names are case insensitive so no need to uppercase them.

  * ``celeries``: list of Celery application settings. Each item has the
    following keys available:

    * ``modules``: list of modules where this application is used. Inside each
      of these modules, you can use :func:`kit.Celery` to recover this
      configured application. The application's name will be automatically
      generated from this list of modules.
    * ``kwargs``: dctionary of keyword arguments passed to the
      :class:`celery.Celery` constructor.
    * ``config``: dicionary of configuration options used to configure the
      application. Names are case insensitive so no need to uppercase them.

  * ``sessions: dictionary of sessions. The key is the session name (used
    as argument to :func:`kit.get_sessions`). Each item has the following
    settings available:

    * ``url``: the database url (defaults to ``sqlite://``)
    * ``kwargs``: dictionary of keyword arguments to pass to
      ``sqlalchemy.orm.sessionmaker``.
    * ``engine``: dictionary of keyword arguments to pass to the bound engine's
      constructor.
    * ``options``: there are currently two options available:

      * ``commit``: whether or not to commit the session after each request
        or task (defaults to ``False``).
      * ``raise``: whether or not to reraise any errors found during commit
        (defaults to ``True``).

Note that there can only be one application of each type (Flask or Celery) in
a module. This shouldn't be too restrictive as it is arguable bad practice to
mix applications in a same module.

Command line tool
-----------------

``kit -h``


Next steps
----------

Todo.


All the functions available in the ``kit`` module are detailed below:

"""

__version__ = '0.2.4'


def Flask(module_name, path=None):
  """Returns the Flask application registered for the module.

  :param module_name: the module name for which to get the application.
    Typically, this should always be set to ``__name__``.
  :type module_name: str
  :param path: the path to the overall kit configuration file. This can be used
    to load the Flask application outside of the kit command line tool.
  :type path: str
  :rtype: `flask.Flask`

  .. note::

    This isn't a class constructor.

  """
  from .base import Kit
  return Kit(path).get_flask_app(module_name)

def Celery(module_name, path=None):
  """Returns the Celery application registered for the module.

  :param module_name: the module name for which to get the application.
    Typically, this should always be set to ``__name__``.
  :type module_name: str
  :param path: the path to the overall kit configuration file. This can be used
    to load the Celery application outside of the kit command line tool.
  :type path: str
  :rtype: `celery.Celery`

  .. note::

    This isn't a class constructor.

  """
  from .base import Kit
  return Kit(path).get_celery_app(module_name)

def get_session(session_name, path=None):
  """Returns the corresponding session.

  :param session_name: the key of the session in the configuration file.
  :type session_name: str
  :param path: the path to the overall kit configuration file. This can be used
    to load the sessions outside of the kit command line tool.
  :type path: str
  :rtype: `sqlalchemy.orm.scoping.scoped_session`

  """
  from .base import Kit
  return Kit(path).get_session(session_name)

def get_config(path=None):
  """Returns the kit's configuration.

  :param path: the path to the overall kit configuration file. This can be used
    to load the configuration outside of the kit command line tool.
  :type path: str
  :rtype: dict

  """
  from .base import Kit
  return Kit(path).config

def teardown_handler(func, path=None):
  """Set the teardown handler.

  :param func: Must accept three arguments: session, app,
    session_options
  :type func: callable

  """
  from .base import Kit
  Kit(path)._teardown_handler = func

def get_kit(path=None):
  from .base import Kit
  return Kit(path)
