#!/usr/bin/env python

"""Global configuration module."""

# General imports

from os.path import abspath, dirname, join, pardir

# Logging configuration

LOGGING_FOLDER = abspath(join(dirname(__file__), pardir, 'logs'))
LOGGER_CONFIG = {
    'version': 1,              
    'formatters': {
        'standard': {
            'format': '%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level':'INFO',    
            'class':'logging.FileHandler',
            'formatter': 'standard',
            'filename': join(LOGGING_FOLDER, 'info.log')
        },  
        'stream': {
            'level':'INFO',    
            'class':'logging.StreamHandler',
            'formatter': 'standard',
        },  
    },
    'loggers': {
        '': {
            'handlers': ['default', 'stream'],
            'level': 'INFO',
            'propagate': True
        },
    }
}
DEBUG_LOGGER_CONFIG = {
    'version': 1,              
    'formatters': {
        'standard': {
            'format': '%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level':'DEBUG',    
            'class':'logging.FileHandler',
            'formatter': 'standard',
            'filename': join(LOGGING_FOLDER, 'info.log')
        },  
        'stream': {
            'level':'INFO',    
            'class':'logging.StreamHandler',
            'formatter': 'standard',
        },  
    },
    'loggers': {
        '': {
            'handlers': ['default', 'stream'],
            'level': 'DEBUG',
            'propagate': True
        },
    }
}
