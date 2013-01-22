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

import oauth

# Creating the manager instance
# =============================

def make(project_name, factory, db, celery, use_oauth):

  manager = Manager(factory, with_default_commands=False)

  # Options
  # these options seem to be passed to the make_app function and also added
  # to the current_app instance
  manager.add_option(
      '-d', '--debug', action='store_true', dest='debug', default=False
  )

  # Commands
  manager.add_command('shell', Shell())

  @manager.shell
  def make_shell_context():
    db.create_connection()
    return {
      'app': current_app,
      'db': db,
      'celery': celery,
    }

  @manager.option('-t', '--host', dest='host', default='0.0.0.0')
  @manager.option('-p', '--port', dest='port', default=5000)
  def run_server(host, port):
    """Start the flask werkzeug server."""
    db.create_connection(app=current_app)
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

  if use_oauth:

    @manager.command
    def add_user():
      """Add user to database."""
      db.create_connection()
      with db as session:
        user_email = prompt('User email?')
        user = oauth.User(user_email)
        session.add(user)

    @manager.command
    def view_users():
      """View all database users."""
      db.create_connection()
      with db as session:
        users = session.query(oauth.User).all()
        for user in users:
          print '%10s %s' % (user.id, user.email)

    @manager.command
    def remove_user():
      """Remove user."""
      db.create_connection()
      with db as session:
        users = session.query(oauth.User).all()
        for user in users:
          print '%10s %s' % (user.id, user.email)
        user_id = prompt('User id?')
        session.delete(oauth.User.query.get(user_id))

  if celery:

    @manager.command
    def run_worker():
      """Start the Celery worker."""
      if current_app.debug:
        celery.worker_main([
          'worker',
          '--beat',
          '--schedule=%s/production.sch' % celery.conf['SCHEDULES_FOLDER'],
          '--hostname=development.%s' % project_name,
          '--queues=development'
        ])
      else:
        celery.worker_main([
          'worker',
          '--beat',
          '--schedule=%s/development.sch' % celery.conf['SCHEDULES_FOLDER'],
          '--hostname=production.%s' % project_name,
          '--queues=production'
        ])

    @manager.option('-p', '--port', dest='port', default='5555')
    def run_flower(port):
      """Run flow manager."""
      celery.start([
        'celery',
        'flower',
        '--broker=%s' % celery.conf['BROKER_URL'],
        '--port=%s' % port
      ])

  return manager
