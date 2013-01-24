#!/usr/bin/env python

from flask.ext.script import Manager, prompt, Shell

from project import current_project

project = current_project

manager = Manager(project.make, with_default_commands=False)
# these options seem to be passed to the make_app function and
# also added  to the current_app instance
manager.add_option(
    '-d', '--debug', action='store_true', dest='debug', default=False
)

# Start a new project
# This command will actually never get executed by this manager but is here
# for the help text
@manager.command
def new():
  """Start a new project."""
  pass

# Shell

manager.add_command('shell', Shell())

@manager.shell
def make_shell_context():
  project.db.create_connection()
  return {'app': project.app, 'db': project.db, 'celery': project.celery}

# Server

@manager.option('-t', '--host', dest='host', default='0.0.0.0')
@manager.option('-p', '--port', dest='port', default=5000)
def server(host, port):
  """Start the flask werkzeug server."""
  project.db.create_connection(app=project.app)
  project.app.run(host=host, port=int(port), debug=project.app.debug)

@manager.command
def view_app_config():
  """View config currently used by the app."""
  print 'App config:'
  for key, value in sorted(project.app.config.items()):
    print '%30s %s' % (key, value)

# OAuth

if project.use_oauth():

  @manager.command
  def add_user():
    """Add user to database."""
    project.db.create_connection()
    with project.db as session:
      user_email = prompt('User email?')
      user = oauth.User(user_email)
      session.add(user)

  @manager.command
  def view_users():
    """View all database users."""
    project.db.create_connection()
    with project.db as session:
      users = session.query(oauth.User).all()
      for user in users:
        print '%10s %s' % (user.id, user.email)

  @manager.command
  def remove_user():
    """Remove user."""
    project.db.create_connection()
    with project.db as session:
      users = session.query(oauth.User).all()
      for user in users:
        print '%10s %s' % (user.id, user.email)
      user_id = prompt('User id?')
      session.delete(oauth.User.query.get(user_id))

# Celery

@manager.command
def worker():
  """Start the Celery worker."""
  hostname = project.NAME.lower().replace(' ', '_')
  if project.app.debug:
    project.celery.worker_main([
      'worker',
      '--beat',
      '--schedule=%s/production.sch' % project.CELERY_SCHEDULE_FOLDER,
      '--hostname=development.%s' % hostname,
      '--queues=development'
    ])
  else:
    project.celery.worker_main([
      'worker',
      '--beat',
      '--schedule=%s/development.sch' % project.CELERY_SCHEDULE_FOLDER,
      '--hostname=production.%s' % hostname,
      '--queues=production'
    ])

# Flower

@manager.option('-p', '--port', dest='port', default='5555')
def flower(port):
  """Run flow manager."""
  project.celery.start([
    'celery',
    'flower',
    '--broker=%s' % project.celery.conf['BROKER_URL'],
    '--port=%s' % port
  ])

manager.run()
