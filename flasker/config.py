#!/usr/bin/env python

"""Global configuration module."""

from os.path import abspath, dirname, join, pardir

APP_FOLDER = abspath(join(dirname(__file__), pardir))

#
# REQUIRED ====================================================================
#

# A title for the project (letters and underscores only)

PROJECT_NAME = 'project_name'

# The URL to the database (can be sqlite filepath, mysql url, etc.)
#
# Examples:
#
# * 'sqlite:///%s/core/db/app.sqlite' % APP_FOLDER
# * 'mysql://db_user:dp_pass@localhost/db_name'

DB_URL = 'sqlite:///%s/core/db/app.sqlite' % APP_FOLDER

#
# OPTIONAL ====================================================================
#

# To use Celery

USE_CELERY = False
BROKER_URL = 'redis://localhost:6379/0'

# To use Google Auth (secret key can be generated using os.urandom(24))

USE_OAUTH = False
GOOGLE_CLIENT_ID = ''
GOOGLE_CLIENT_SECRET = ''
SECRET_KEY = '\x81K\xfb4u\xddp\x1c>\xe2e\xeeI\xf2\xff\x16\x16\xf6\xf9D'

# To serve resources from another server, enter the url here (no trailing slash)

STATIC_SERVER_URL = ''

#
# UNDER THE HOOD ==============================================================
#

class BaseConfig(object):

  """Base app configuration."""

  APP_DB_URL = DB_URL
  DEBUG = False
  LOGGER_NAME = 'app'
  SECRET_KEY = SECRET_KEY
  USE_X_SENDFILE = False
  TESTING = False

class DebugConfig(BaseConfig):

  """Debug app configuration.
  
  Note the SEND_FILE_MAX_AGE_DEFAULT = 1 to force refresh on every load. This
  makes debugging javascript much easier but also slows down page loads
  significantly.
  
  """

  DEBUG = True
  TESTING = True
  SEND_FILE_MAX_AGE_DEFAULT = 1
  USE_X_SENDFILE = False

class LoggerConfig(object):

  """Logger configuration."""

  LOGGING_FOLDER = abspath(join(dirname(__file__), pardir, 'core', 'logs'))
  LOGGER_CONFIG = {
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
        'filename': join(LOGGING_FOLDER, 'info.log')
      },  
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
      },
      'app': {
        'handlers': ['file'],
        'level': 'INFO',
        'propagate': True
      },
      'celery': {
        'handlers': ['file'],
        'level': 'INFO',
        'propagate': True
      },
    }
  }
  DEBUG_LOGGER_CONFIG = {
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
        'filename': join(LOGGING_FOLDER, 'debug.log')
      },  
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
      'app': {
        'handlers': ['file'],
        'level': 'DEBUG',
        'propagate': True
      },
      'celery': {
        'handlers': ['file'],
        'level': 'DEBUG',
        'propagate': True
      },
    }
  }

if USE_CELERY:

  from kombu import Exchange, Queue

  exchange = Exchange(PROJECT_NAME, type='direct')

  class CeleryBaseConfig(object):

    """Base Celery configuration."""

    DEBUG = False
    BROKER_URL = BROKER_URL
    CELERY_QUEUES = [
      Queue(
        'production',
        exchange=exchange,
        routing_key='production.%s' % PROJECT_NAME
      ),
      Queue(
        'development',
        exchange=exchange,
        routing_key='development.%s' % PROJECT_NAME
      )
    ]
    CELERY_DEFAULT_EXCHANGE = exchange
    CELERY_DEFAULT_ROUTING_KEY = 'production.%s' % PROJECT_NAME
    CELERY_DEFAULT_QUEUE = 'production'
    CELERY_DISABLE_RATE_LIMIT = True
    CELERY_RESULT_BACKEND = BROKER_URL
    CELERY_SEND_EVENTS = True
    CELERY_TASK_RESULT_EXPIRES = 3600
    CELERY_TRACK_STARTED = True
    CELERYD_CONCURRENCY = 3
    CELERYD_PREFETCH_MULTIPLIER = 1

  class CeleryDebugConfig(CeleryBaseConfig):

    """Debug Celery configuration."""

    DEBUG = True
    CELERY_DEFAULT_ROUTING_KEY = 'development.%s' % PROJECT_NAME
    CELERY_DEFAULT_QUEUE = 'development'

if USE_OAUTH:

  class AuthConfig(object):

    """Authentication blueprint configuration."""

    CLIENT_ID = GOOGLE_CLIENT_ID
    CLIENT_SECRET = GOOGLE_CLIENT_SECRET

