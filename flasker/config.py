#!/usr/bin/env python

"""Global configuration module."""

import logging
from logging import getLogger, StreamHandler
from kombu import Exchange, Queue
from os.path import abspath, join

class BaseConfig(object):

  """Base config class.

  The DEFAULT and DEBUG dictionaries will take precedence on any other
  settings.  This allows new configurations by simply subclassing and
  implementing these two entries.
  
  """

  DEFAULT = {}
  DEBUG = {}

  @classmethod
  def default(cls, project):
    return cls.DEFAULT

  @classmethod
  def debug(cls, project):
    return cls.DEBUG

  @classmethod
  def generate(cls, project):
    rv = cls.default(project)
    rv.update(cls.DEFAULT)
    if project.debug:
      rv.update(cls.debug(project))
      rv.update(cls.DEBUG)
    return rv

class AppConfig(BaseConfig):

  """Base app configuration."""

  @classmethod
  def default(cls, project):
    return {
      'DEBUG': False,
      'LOGGER_NAME': 'app',
      'SECRET_KEY': '\x81K\xfb4u\xddp\x1c>\xe2e\xeeI\xf2\xff\x16\x16\xf6\xf9D',
      'USE_X_SENDFILE': False,
      'TESTING': False
    }

  @classmethod
  def debug(cls, project):
    return {
      'DEBUG': True,
      'TESTING': True,
      'SEND_FILE_MAX_AGE_DEFAULT': 1,
      'USE_X_SENDFILE': False
    }

class CeleryConfig(BaseConfig):

  """Base Celery configuration."""

  @classmethod
  def default(cls, project):
    hostname = project.NAME.lower().replace(' ', '_')
    exchange = Exchange(hostname, type='direct')
    return {
      'DEBUG': False,
      'BROKER_URL': 'redis://localhost:6379/0',
      'CELERY_QUEUES': [
        Queue(
          'production',
          exchange=exchange,
          routing_key='production.%s' % hostname
        ),
        Queue(
          'development',
          exchange=exchange,
          routing_key='development.%s' % hostname
        )
      ],
      'CELERY_DEFAULT_EXCHANGE': exchange,
      'CELERY_DEFAULT_ROUTING_KEY': 'production.%s' % hostname,
      'CELERY_DEFAULT_QUEUE': 'production',
      'CELERY_DISABLE_RATE_LIMIT': True,
      'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
      'CELERY_SEND_EVENTS': True,
      'CELERY_TASK_RESULT_EXPIRES': 3600,
      'CELERY_TRACK_STARTED': True,
      'CELERYD_CONCURRENCY': 3,
      'CELERYD_PREFETCH_MULTIPLIER': 1,
    }

  @classmethod
  def debug(cls, project):
    hostname = project.NAME.lower().replace(' ', '_')
    return {
      'DEBUG': True,
      'CELERY_DEFAULT_ROUTING_KEY': 'development.%s' % hostname,
      'CELERY_DEFAULT_QUEUE': 'development'
    }

class LoggerConfig(BaseConfig):

  """Logger configuration."""

  @classmethod
  def default(cls, project):
    logging_folder = abspath(project.LOGGING_FOLDER)
    return {
      'version': 1,        
      'formatters': {
        'standard': {
          'format': '%(asctime)s : %(name)s : %(levelname)s :: %(message)s'
        },
      },
      'handlers': {
        'stream': {
          'level':'WARN',  
          'class':'logging.StreamHandler',
          'formatter': 'standard',
        },  
        'file': {
          'level':'INFO',    
          'class':'logging.FileHandler',
          'formatter': 'standard',
          'filename': join(logging_folder, 'info.log')
        },
      },
      'root': {
        'handlers': ['stream', 'file'],
        'level': 'INFO',
      },
    }

  @classmethod
  def debug(cls, project):
    logging_folder = abspath(project.LOGGING_FOLDER)
    return {
      'version': 1,        
      'formatters': {
        'standard': {
          'format': '%(asctime)s : %(name)s : %(levelname)s :: %(message)s'
        },
      },
      'handlers': {
        'stream': {
          'level':'DEBUG',  
          'class':'logging.StreamHandler',
          'formatter': 'standard',
        },  
        'file': {
          'level':'DEBUG',    
          'class':'logging.FileHandler',
          'formatter': 'standard',
          'filename': join(logging_folder, 'debug.log')
        },
      },
      'root': {
        'handlers': ['stream', 'file'],
        'level': 'DEBUG',
      },
    }

