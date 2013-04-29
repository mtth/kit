#!/usr/bin/env python

"""PYPI setup module."""

from setuptools import find_packages, setup

def get_version():
  from kit import __version__
  return __version__

def get_description():
  from kit import __doc__
  return __doc__.strip('Kit: ')

setup(
    name='kit',
    version=get_version(),
    description=get_description(),
    long_description=open('README.rst').read(),
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
      'pyyaml',
      'docopt',
      'flask',
      'celery',
      'sqlalchemy',
      'blinker',
    ],
    entry_points={'console_scripts': ['kit = kit.__main__:main']},
)
