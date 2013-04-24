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


def get_flask_app(name, path=None):

  from .base import Kit
  return Kit(path).get_flask_app(name)

def get_celery_app(name, path=None):

  from .base import Kit
  return Kit(path).get_celery_app(name)

def get_session(name, path=None):

  from .base import Kit
  return Kit(path).get_session(name)
