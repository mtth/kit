#!/usr/bin/env python

"""To load templates."""

from argparse import ArgumentParser, REMAINDER
from code import interact
from distutils.dir_util import copy_tree
from functools import wraps
from os import mkdir
from os.path import abspath, dirname, join
from shutil import copy
from sys import path

from flasker import current_project
from flasker.project import Project, ProjectImportError

# Parsers

# Main parser

parser = ArgumentParser('flasker')

parser.add_argument('-c', '--conf',
  dest='conf',
  default='default.cfg',
  help='path to configuration file [%(default)s]'
)
subparsers = parser.add_subparsers(
  title='available commands',
  dest='command',
)

def project_context(handler):
  """Create the project context.
  
  Some (most) subparser handlers require the project to be created before
  returning, this decorator handles this.

  """
  @wraps(handler)
  def wrapper(*args, **kwargs):
    parsed_args = args[0]
    path.append(abspath(dirname(parsed_args.conf))) # for reloader to work
    try:
      pj = Project(parsed_args.conf)
    except ProjectImportError as e:
      print e
      return
    else:
      pj.make()
      handler(*args, **kwargs)
  return wrapper

# New

new_parser = subparsers.add_parser('new', help='start new project')

new_parser.add_argument('-a', '--app',
  action='store_false',
  help='don\'t include basic bootstrap app template'
)
new_parser.add_argument('-n', '--name',
  default='default.cfg',
  help='name of the new config file [%(default)s]'
)
new_parser.add_argument('config',
  choices=['basic', 'celery_dq'],
  help='the type of config to create'
)

def new_handler(parsed_args):
  src = dirname(__file__)
  copy(join(src, 'configs', '%s.cfg' % parsed_args.config), parsed_args.name)
  print 'Project configuration file created.'
  if parsed_args.app:
    copy_tree(join(src, 'data'), '.')
    print 'Bootstrap app folder created.'
  print 'All set!'

new_parser.set_defaults(handler=new_handler)

# Server

server_parser = subparsers.add_parser('server', help='start server')

server_parser.add_argument('-r', '--restrict',
  default=False,
  action='store_true',
  dest='restrict',
  help='disallow remote server connections'
)
server_parser.add_argument('-p', '--port',
  default=5000,
  type=int,
  help='listen on port [%(default)s]'
)
server_parser.add_argument('-d', '--debug',
  default=False,
  action='store_true',
  help='run in debug mode (autoreload and debugging)'
)

@project_context
def server_handler(parsed_args):
  pj = current_project
  host = '127.0.0.1' if parsed_args.restrict else '0.0.0.0'
  pj.db.create_connection(app=pj.app)
  pj.app.run(host=host, port=parsed_args.port, debug=parsed_args.debug)

server_parser.set_defaults(handler=server_handler)

# Shell

shell_parser = subparsers.add_parser('shell', help='start shell')

@project_context
def shell_handler(parsed_args):
  pj = current_project
  pj.db.create_connection(app=pj.app)
  context = {
    'project': pj,
    'db': pj.db,
    'app': pj.app,
    'celery': pj.celery
  }
  try:
    import IPython
  except ImportError:
    interact(local=context)
  else:
    try:
      sh = IPython.Shell.IPShellEmbed()
    except AttributeError:
      sh = IPython.frontend.terminal.embed.InteractiveShellEmbed()
    sh(global_ns=dict(), local_ns=context)

shell_parser.set_defaults(handler=shell_handler)

# Worker

worker_parser = subparsers.add_parser('worker', help='start worker')

worker_parser.add_argument('-n', '--name',
  default='',
  help='hostname prefix'
)
worker_parser.add_argument('-Q', '--queues',
  help='queues (comma separated)'
)
worker_parser.add_argument('-B', '--beat',
  default=False,
  action='store_true',
  help='run with celerybeat'
)
worker_parser.add_argument('-v', '--verbose-help',
  default=False,
  action='store_true',
  help='show full help from celery worker'
)
worker_parser.add_argument('-r', '--raw',
  nargs=REMAINDER,
  help='raw options to pass through',
)

@project_context
def worker_handler(parsed_args):
  pj = current_project
  pj.db.create_connection(celery=pj.celery)
  if parsed_args.verbose_help:
    pj.celery.worker_main(['worker', '-h'])
  else:
    domain = pj.config['PROJECT']['SHORTNAME']
    subdomain = parsed_args.name or pj.config['PROJECT']['CONFIG']
    options = ['worker', '--hostname=%s.%s' % (subdomain, domain)]
    if parsed_args.queues:
      options.append('--queues=%s' % parsed_args.queues)
    if parsed_args.beat:
      options.append('--beat')
    if parsed_args.raw:
      options.extend(parsed_args.raw)
    pj.celery.worker_main(options)

worker_parser.set_defaults(handler=worker_handler)

# Flower

flower_parser = subparsers.add_parser('flower', help='start flower')

flower_parser.add_argument('-p', '--port',
  default=5555,
  type=int,
  help='listen on port [%(default)s]'
)
flower_parser.add_argument('-v', '--verbose-help',
  default=False,
  action='store_true',
  help='show full help from celery flower'
)
flower_parser.add_argument('-r', '--raw',
  help='raw options to pass through',
  nargs=REMAINDER
)

@project_context
def flower_handler(parsed_args):
  pj = current_project
  if parsed_args.verbose_help:
    pj.celery.start(['celery', 'flower', '--help'])
  else:
    options = ['celery', 'flower', '--port=%s' % parsed_args.port]
    if parsed_args.raw:
      options.extend(parsed_args.raw)
    pj.celery.start(options)

flower_parser.set_defaults(handler=flower_handler)

# END of parsers

def main():
  parsed_args = parser.parse_args()
  parsed_args.handler(parsed_args)

if __name__ == '__main__':
  main()
