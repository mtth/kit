#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='flasker',
    version='0.1.0',
    description='Flasker',
    long_description=open('README.rst').read(),
    author='Matthieu Monsch',
    author_email='monsch@mit.edu',
    url='https://github.com/mtth/flasker',
    license='MIT',
    packages=find_packages(),
    install_requires=[
      'celery',
      'flask',
      'flask-script',
      'flask-login',
      'sqlalchemy',
      'redis',
      'flower'
    ],
    package_data={'flasker': ['templates/*']}
)
