#!/usr/bin/env python

"""Kit: Flask, Celery, SQLAlchemy integration framework."""

__version__ = '0.2.13'


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
