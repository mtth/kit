#!/usr/bin/env python

"""Global configuration module."""

from os.path import abspath, dirname, join, pardir

APPLICATION_FOLDER = abspath(join(dirname(__file__), pardir))

#
# REQUIRED ====================================================================
#

# The URL to the database (can be sqlite filepath, mysql url, etc.)
#
# Examples:
#
# * 'sqlite:///%s/core/db/app.sqlite' % APPLICATION_FOLDER
# * 'mysql://db_user:dp_pass@localhost/db_name'

DB_URL = 'sqlite:///%s/core/db/app.sqlite' % APPLICATION_FOLDER

#
# OPTIONAL ====================================================================
#

# To use Google Auth 

USE_OAUTH = False
GOOGLE_CLIENT_ID = ''
GOOGLE_CLIENT_SECRET = ''

# To activate the Celery backend

USE_CELERY = False

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
  SECRET_KEY = '\x81K\xfb4u\xddp\x1c>\xe2e\xeeI\xf2\xff\x16\x16\xf6\xf9D'
  USE_X_SENDFILE = True
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

class AuthConfig(object):

  """Authentication blueprint configuration."""

  CLIENT_ID = GOOGLE_CLIENT_ID
  CLIENT_SECRET = GOOGLE_CLIENT_SECRET

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
        'level':'DEBUG',    
        'class':'logging.StreamHandler',
        'formatter': 'standard',
      },  
    },
    'loggers': {
      '': {
        'handlers': ['stream'],
        'level': 'DEBUG',
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

class CeleryBaseConfig(object):

  """Base Celery configuration."""

  DEBUG = False
  BROKER_URL = 'redis://localhost:6379/0'
  CELERY_DISABLE_RATE_LIMIT = True
  CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
  CELERYD_CONCURRENCY = 3
  CELERYD_PREFETCH_MULTIPLIER = 1
  CELERY_IMPORTS = (
      'app.core.celery',
      'app.tasks',
  )

class CeleryDebugConfig(CeleryBaseConfig):

  """Debug Celery configuration.

  Note that the broker url is different than the base Celery one. This seems
  to be necessary so that the workers have completely separate tasks.

  """

  DEBUG = True
  BROKER_URL = 'redis://localhost:6379/1'
  CELERY_RESULT_BACKEND = 'redis://localhost:6379/1'
