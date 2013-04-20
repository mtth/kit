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
documentation and examples!

"""

from setuptools import find_packages, setup

def get_version():
  from kit import __version__
  return __version__

setup(
    name='kit',
    version=get_version(),
    description='Flask, Celery, SQLAlchemy toolkit',
    long_description=__doc__,
    author='Matthieu Monsch',
    author_email='monsch@mit.edu',
    url='http://github.com/mtth/kit/',
    license='MIT',
    packages=find_packages(),
    classifiers=[
      'Development Status :: 4 - Beta',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Programming Language :: Python',
    ],
    install_requires=[
      'blinker',
      'pyyaml',
    ],
    entry_points={'console_scripts': ['kit = kit.__main__:main']},
)
