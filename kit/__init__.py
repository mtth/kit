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


def flasks(name=None, path=None):

  from .base import Kit
  return Kit(path).get_flasks(name)

def celeries(name=None, path=None):

  from .base import Kit
  return Kit(path).get_celeries(name)

def sessions(name=None, path=None):

  from .base import Kit
  return Kit(path).get_sessions(name)
