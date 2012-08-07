#!/usr/bin/env python

"""Flask App Template helpers"""

# General imports

from datetime import datetime

from functools import partial

from json import dumps, loads

# Helpers
# =======

class Loggable(object):

    """To easily access stored instances properties and log stuff."""

    def jsonify(self):
        d = {}
        varnames = [
                e for e in dir(self)
                if not e.startswith('_')
                if not e == 'metadata'
        ]
        for varname in attributes:
            value = getattr(self, varname)
            if isinstance(value, (dict, float, int, str)):
                d[varname] = getattr(self, value)
            elif isinstance(value, datetime):
                d[varname] = getattr(self, str(value))
        return d

    def _logger(self, message, loglevel):
        action = getattr(logger, loglevel)
        return action('%s :: %s' % (self, message))

    def __getattr__(self, varname):
        if varname in ['debug', 'info', 'warn', 'error']:
            return partial(self._logger, loglevel=varname)
        else:
            raise AttributeError

def pagify(func):
    """Adds pagination to views."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'p' in request.args:
            page = max(0, int(request.args['p']) - 1)
        else:
            page = 0
        return func(*args, page=page, **kwargs)
    return wrapper
