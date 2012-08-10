#!/usr/bin/env python

"""Application manager.

Command line interface to:

*   Start web server
*   Start celery worker
*   Manage database (maybe?)

Comments
--------

Note that the session doesn't need to be initialized here. This is because
calling `manager.run` instantiates the app which automatically creates the
database connection at that moment. Pretty nifty and convenient.

"""

from flask import current_app
from flask.ext.script import Manager, prompt, Shell

from pprint import pprint

from subprocess import call

from sys import modules

from app import make_app
from app.auth.models import User
from app.core.database import Session

import app.models as m

# Creating the manager instance
# =============================

manager = Manager(make_app, with_default_commands=False)

# Options
# these options seem to be passed to the make_app function and also added
# to the current_app instance
manager.add_option(
        '-d', '--debug', action='store_true', dest='debug', default=False
)

manager.add_command('shell', Shell())

# App management
# ==============

@manager.option('-t', '--host', dest='host', default='0.0.0.0')
@manager.option('-p', '--port', dest='port', default=5000)
def run_server(host, port):
    """Start the flask werkzeug server."""
    current_app.run(
            host=host,
            port=port,
            debug=current_app.debug
    )

@manager.command
def view_app_config():
    """View config currently used by the app."""
    print 'App config:'
    for key, value in sorted(current_app.config.items()):
        print '%30s %s' % (key, value)

@manager.command
def add_user():
    with Session() as session:
        user_email = prompt('User email?')
        user = User(user_email)
        session.add(user)
        session.commit()

@manager.command
def view_users():
    with Session() as session:
        users = session.query(User).all()
        for user in users:
            print '%10s %s' % (user.id, user.email)

def promote_user():
    pass

# Celery management
# =================

@manager.command
def run_worker():
    """Start the Celery worker."""
    if current_app.debug:
        print 'Starting Celery worker in DEBUG mode!'
        call([
                'celery', 'worker',
                '--config=app.config.celery.celery_debug',
                '--loglevel=debug',
        ])
    else:
        print 'Starting Celery worker!'
        call([
                'celery', 'worker',
                '--config=app.config.celery.celery_base',
                '--loglevel=info',
        ])

@manager.command
def view_celery_config():
    """View config used by the Celery worker."""
    print 'Celery config:'
    if current_app.debug:
        module = 'app.config.celery.celery_debug'
    else:
        module = 'app.config.celery.celery_base'
    __import__(module)
    mod = modules[module]
    for key in dir(mod):
        if not key.startswith('_'):
            print '%30s %s' % (key, getattr(mod, key))

if __name__ == '__main__':
    manager.run()
