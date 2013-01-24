#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='flasker',
    version='0.1.2',
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
    package_data={'flasker': ['components/templates/*']},
    entry_points={'console_scripts': ['flasker = flasker.__main__:main']},
    # data_files=[
    #   ('example', ['example/manage.py']),
    #   ('example/app', [
    #     'example/app/project.py',
    #     'example/app/views.py',
    #     'example/app/__init__.py',
    #   ])
    # ]
)
