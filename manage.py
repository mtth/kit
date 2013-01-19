#!/usr/bin/env python

"""Application manager.

Command line interface to:

* Start web server
* Start celery worker
* Manage database

Comments
--------

Note that the session doesn't need to be initialized here. This is because
calling `manager.run` instantiates the app which automatically creates the
database connection at that moment. Pretty nifty and convenient.

"""

from flask import current_app
from flask.ext.script import Manager, prompt, Shell

from app import make_app
from app.core.config import USE_CELERY, USE_OAUTH
from app.core.database import db

if USE_CELERY:
  from app import celery

if USE_OAUTH:
  from app.core.auth import User

# Creating the manager instance
# =============================

manager = Manager(make_app, with_default_commands=False)

# Options
# these options seem to be passed to the make_app function and also added
# to the current_app instance
manager.add_option(
    '-d', '--debug', action='store_true', dest='debug', default=False
)

# Commands
manager.add_command('shell', Shell())

# App management
# ==============

@manager.option('-t', '--host', dest='host', default='0.0.0.0')
@manager.option('-p', '--port', dest='port', default=5000)
def run_server(host, port):
  """Start the flask werkzeug server."""
  db.create_connection(debug=current_app.debug, app=current_app)
  current_app.run(
      host=host,
      port=int(port),
      debug=current_app.debug
  )

@manager.command
def view_app_config():
  """View config currently used by the app."""
  print 'App config:'
  for key, value in sorted(current_app.config.items()):
    print '%30s %s' % (key, value)

if USE_OAUTH:

  @manager.command
  def add_user():
    """Add user to database."""
    with db() as session:
      user_email = prompt('User email?')
      user = User(user_email)
      session.add(user)
      session.commit()

  @manager.command
  def view_users():
    """View all database users."""
    with db() as session:
      users = session.query(User).all()
      for user in users:
        print '%10s %s' % (user.id, user.email)

# Celery management
# =================

if USE_CELERY:

  @manager.command
  def run_worker():
    """Start the Celery worker."""
    celery.worker_main(['worker'])

  @manager.option('-p', '--port', dest='port', default='5555')
  def run_flower(port):
    """Run flow manager."""
    celery.start(['celery', 'flower', '--port=%s' % port])

if __name__ == '__main__':
  manager.run()
