#!/usr/bin/env python

"""
Kit
===

Your friendly Flask, Celery, SQLAlchemy toolkit.

Why use Kit?
------------

* 1 YAML file for all your configuration options
* A command line tool to start a development server, Celery workers and more
* Seamless integration between SQLAlchemy and the rest of your application

How to get Kit?
---------------

.. code:: bash

  pip install kit

You can find the latest version on `Github <https://github.com/mtth/kit>`_.

"""

__version__ = '0.1.18'


def Flask(module_name, path=None):
  """Returns Flask application registered for module.

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
  """Returns Celery application registered for module.

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

def get_sessions(path=None):
  """Returns all the sessions registered for this kit.

  :param path: the path to the overall kit configuration file. This can be used
    to load the sessions outside of the kit command line tool.
  :type path: str
  :rtype: list

  """
  from .base import Kit
  return Kit(path).sessions

def get_config(path=None):
  """Returns the kit's configuration.

  :param path: the path to the overall kit configuration file. This can be used
    to load the configuration outside of the kit command line tool.
  :type path: str
  :rtype: dict

  """
  from .base import Kit
  return Kit(path).config
