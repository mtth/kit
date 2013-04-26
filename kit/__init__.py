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

  from .base import Kit
  return Kit(path).get_flask_app(module_name)

def Celery(module_name, path=None):

  from .base import Kit
  return Kit(path).get_celery_app(module_name)

def get_sessions(path=None):
  
  from .base import Kit
  return Kit(path).get_sessions()

def get_config(path=None):

  from .base import Kit
  return Kit(path).config
