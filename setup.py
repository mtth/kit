#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='flasker',
    version='0.1.18',
    description='Flask, SQLAlchemy and Celery integration tool.',
    long_description=open('README.rst').read(),
    author='Matthieu Monsch',
    author_email='monsch@mit.edu',
    url='https://github.com/mtth/flasker',
    license='MIT',
    packages=find_packages(),
    classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Topic :: System :: Distributed Computing',
      'Programming Language :: Python',
    ],
    install_requires=[
      'celery',
      'flask',
      'flask-login',
      'sqlalchemy',
      'redis',
      'flower'
    ],
    package_data={'flasker': [
      'components/templates/*',
      'configs/*',
      'data/**/**/*',
    ]},
    include_package_data=True,
    entry_points={'console_scripts': ['flasker = flasker.__main__:main']},
)
