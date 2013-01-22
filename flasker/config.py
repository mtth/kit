#!/usr/bin/env python

"""Global configuration module."""

from kombu import Exchange, Queue
from os.path import join

def make(project_name, project_root, logging_folder, celery_folder, debug):

  class AppBaseConfig(object):

    """Base app configuration."""

    # Activating this messes up sessions...
    # APPLICATION_ROOT = project_root
    DEBUG = False
    LOGGER_NAME = 'app'
    SECRET_KEY = '\x81K\xfb4u\xddp\x1c>\xe2e\xeeI\xf2\xff\x16\x16\xf6\xf9D'
    USE_X_SENDFILE = False
    TESTING = False

  class AppDebugConfig(AppBaseConfig):

    """Debug app configuration.
    
    Note the SEND_FILE_MAX_AGE_DEFAULT = 1 to force refresh on every load. This
    makes debugging javascript much easier but also slows down page loads
    significantly.
    
    """

    DEBUG = True
    TESTING = True
    SEND_FILE_MAX_AGE_DEFAULT = 1
    USE_X_SENDFILE = False

  if logging_folder:

    class LoggerConfig(object):

      """Logger configuration."""

      BASE_CONFIG = {
        'version': 1,        
        'formatters': {
          'standard': {
            'format': '%(asctime)s : %(name)s : %(levelname)s :: %(message)s'
          },
        },
        'handlers': {
          'file': {
            'level':'INFO',  
            'class':'logging.FileHandler',
            'formatter': 'standard',
            'filename': join(logging_folder, 'info.log')
          },  
          'stream': {
            'level':'WARN',  
            'class':'logging.StreamHandler',
            'formatter': 'standard',
          },  
        },
        'loggers': {
          '': {
            'handlers': ['stream', 'file'],
            'level': 'INFO',
            'propagate': True
          },
        }
      }
      DEBUG_CONFIG = {
        'version': 1,        
        'formatters': {
          'standard': {
            'format': '%(asctime)s : %(name)s : %(levelname)s :: %(message)s'
          },
        },
        'handlers': {
          'file': {
            'level':'DEBUG',    
            'class':'logging.FileHandler',
            'formatter': 'standard',
            'filename': join(logging_folder, 'debug.log')
          },  
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

  else:

    class LoggerConfig(object):

      """Logger configuration."""

      BASE_CONFIG = {
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
            'level': 'WARN',
            'propagate': True
          }
        }
      }
      DEBUG_CONFIG = {
        'version': 1,        
        'formatters': {
          'standard': {
            'format': '%(asctime)s : %(name)s : %(levelname)s :: %(message)s'
          },
        },
        'handlers': {
          'stream': {
            'level':'INFO',    
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

  code_name = project_name.lower().replace(' ', '_')
  exchange = Exchange(code_name, type='direct')

  class CeleryBaseConfig(object):

    """Base Celery configuration."""

    DEBUG = False
    BROKER_URL = 'redis://localhost:6379/0' 
    CELERY_QUEUES = [
      Queue(
        'production',
        exchange=exchange,
        routing_key='production.%s' % code_name
      ),
      Queue(
        'development',
        exchange=exchange,
        routing_key='development.%s' % code_name
      )
    ]
    CELERY_DEFAULT_EXCHANGE = exchange
    CELERY_DEFAULT_ROUTING_KEY = 'production.%s' % code_name
    CELERY_DEFAULT_QUEUE = 'production'
    CELERY_DISABLE_RATE_LIMIT = True
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0' 
    CELERY_SEND_EVENTS = True
    CELERY_TASK_RESULT_EXPIRES = 3600
    CELERY_TRACK_STARTED = True
    CELERYD_CONCURRENCY = 3
    CELERYD_PREFETCH_MULTIPLIER = 1
    SCHEDULES_FOLDER = celery_folder

  class CeleryDebugConfig(CeleryBaseConfig):

    """Debug Celery configuration."""

    DEBUG = True
    CELERY_DEFAULT_ROUTING_KEY = 'development.%s' % code_name
    CELERY_DEFAULT_QUEUE = 'development'

  if debug:
    return {
      'app': AppDebugConfig,
      'celery': CeleryDebugConfig,
      'logger': LoggerConfig.DEBUG_CONFIG
    }
  else:
    return {
      'app': AppBaseConfig,
      'celery': CeleryBaseConfig,
      'logger': LoggerConfig.BASE_CONFIG
    }
