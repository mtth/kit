#!/usr/bin/env python

"""
Kit
===

Your friendly Flask, Celery, SQLAlchemy toolkit.

Why use Kit?
------------

* 1 YAML file for all your configuration options
* No more complicated import schemes for your applications
* Seamless integration between SQLAlchemy and the rest of your application
* A command line tool to start a development server, Celery workers and more

How to get Kit?
---------------

.. code:: bash

  pip install kit

You can find the latest version on `Github <https://github.com/mtth/kit>`_.

"""

__version__ = '0.2.1'


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

def get_kit(path=None):
  from .base import Kit
  return Kit(path)
