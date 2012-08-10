#!/usr/bin/env python

"""Application manager.

Command line interface to:

*   Start web server
*   Start celery worker
*   Manage database (maybe?)

"""

from flask import current_app
from flask.ext.script import Manager

from pprint import pprint

from subprocess import call

from app import make_app
from app.core.database import Session

# Creating the manager instance
# =============================

manager = Manager(make_app)

# Options
# these options seem to be passed to the make_app function
manager.add_option(
        '-d', '--debug', action='store_true', dest='debug', default=False
)

@manager.option('-t', '--host', dest='host', default='0.0.0.0')
@manager.option('-p', '--port', dest='port', default=5000)
def run_server():
    """Start the flask werkzeug server."""
    current_app.run(
            host=host,
            port=port,
            debug=current_app.debug
    )

@manager.command
def run_worker():
    """Start the Celery worker."""
    if current_app.debug:
        print 'Starting debug Celery worker!'
        call(['celery', 'worker', '--config=app.conf.celerydebug'])
    else:
        print 'Starting Celery worker!'
        call(['celery', 'worker', '--config=app.conf.celery'])

if __name__ == '__main__':
    manager.run()
