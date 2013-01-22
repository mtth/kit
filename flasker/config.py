#!/usr/bin/env python

"""Global configuration module."""

from kombu import Exchange, Queue
from os.path import join

class BaseConfig(object):

  """Base config class."""

  @classmethod
  def default(cls, flasker):
    return {}

  @classmethod
  def debug(cls, flasker):
    return {}

  @classmethod
  def get(cls, flasker, debug):
    rv = cls.default(flasker)
    if debug:
      rv.update(cls.debug(flasker))
    return rv

class FlaskerConfig(BaseConfig):

  """Base flasker global configuration."""

  @classmethod
  def default(cls, flasker):
    return {
      'DB_URL': 'sqlite://',
      'LOGGING_FOLDER': None,
      'APP_STATIC_FOLDER': None,
      'APP_TEMPLATE_FOLDER': None,
      'CELERY_SCHEDULE_FOLDER': None,
      'STATIC_URL': None,
      'OAUTH_CREDENTIALS': None,
    }

class AppConfig(BaseConfig):

  """Base app configuration."""

  @classmethod
  def default(cls, flasker):
    return {
      'DEBUG': False,
      'LOGGER_NAME': 'app',
      'SECRET_KEY': '\x81K\xfb4u\xddp\x1c>\xe2e\xeeI\xf2\xff\x16\x16\xf6\xf9D',
      'USE_X_SENDFILE': False,
      'TESTING': False
    }

  @classmethod
  def debug(cls, flasker):
    return {
      'DEBUG': True,
      'TESTING': True,
      'SEND_FILE_MAX_AGE_DEFAULT': 1,
      'USE_X_SENDFILE': False
    }

class LoggerConfig(BaseConfig):

  """Logger configuration."""

  @classmethod
  def default(cls, flasker):
    rv = {
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
      },
      'loggers': {
        '': {
          'handlers': ['stream'],
          'level': 'INFO',
          'propagate': True
        },
      }
    }
    if flasker.config['LOGGING_FOLDER']:
      rv['handlers']['file'] = {
        'level':'DEBUG',    
        'class':'logging.FileHandler',
        'formatter': 'standard',
        'filename': join(logging_folder, 'debug.log')
      }
      rv['loggers']['']['handlers'].append('file')

  @classmethod
  def debug(cls, flasker):
    return {
      'handlers': {
        'file': ,  
        'stream': {
          'level':'INFO',    
          'class':'logging.StreamHandler',
          'formatter': 'standard',
        },  
      },
      'loggers': {
        '': {
          'handlers': ['stream', 'file'],
          'level': 'DEBUG',
          'propagate': True
        },
      }
    }

class CeleryConfig(BaseConfig):

  """Base Celery configuration."""

  @classmethod
  def default(cls, flasker):
    hostname = flasker.name.lower().replace(' ', '_')
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
      'SCHEDULES_FOLDER': celery_folder
    }

  @classmethod
  def debug(cls, flasker):
    return {
      'DEBUG': True,
      'CELERY_DEFAULT_ROUTING_KEY': 'development.%s' % code_name,
      'CELERY_DEFAULT_QUEUE': 'development'
    }
