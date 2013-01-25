#!/usr/bin/env python

"""To load templates."""

from argparse import ArgumentParser, REMAINDER
from code import interact
from distutils.dir_util import copy_tree
from imp import load_source
from os import mkdir
from os.path import abspath, dirname, join
from sys import argv, path

from project import current_project

parser = ArgumentParser('flasker')
parser.add_argument('-c', '--conf',
  dest='conf',
  help='path to configuration file'
)
parser.add_argument('-f', '--file',
  default='project.py',
  help='path to project file [%(default)s]'
)
subparsers = parser.add_subparsers(
  title='available commands',
  dest='command',
#  description='valid subcommands',
#  help='some text help to go here'
)

# New

new_parser = subparsers.add_parser('new', help='start new project')

# auth_parser = subparsers.add_parser(
#   'auth',
#   help='authentication admin'
# )

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

# Shell

shell_parser = subparsers.add_parser('shell', help='start shell')

# Worker

worker_parser = subparsers.add_parser('worker', help='start worker')

worker_parser.add_argument('-n', '--name',
  default='dev',
  help='hostname prefix [%(default)s]'
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

def main():
  args = parser.parse_args()
  print args
  if not args.command:
    parser.print_help()
  elif args.command == 'new':
    choice = raw_input('Start a new project? [y/N] ')
    if choice == 'y':
      src = join(dirname(__file__), 'examples')
      # copy project files
      copy_tree(join(src, '1'), '.')
      # copy html files
      copy_tree(join(src, 'templates'), join('app', 'templates'))
      # create default directories
      mkdir(join('app', 'static'))
      for folder in ['celery', 'db', 'logs']:
        mkdir(folder)
  else:
    try:
      path.append(abspath('.')) # necessary for reloader to work
      load_source('project', args.file)
    except (IOError, ImportError) as e:
      print '%s (%s)' % (e, args.file)
    else:
      current_project.make(True)
      if args.command == 'server':
        host = '127.0.0.1' if args.restrict else '0.0.0.0'
        current_project.db.create_connection(app=current_project.app)
        current_project.app.run(host=host, port=args.port, debug=args.debug)
      elif args.command == 'shell':
        current_project.db.create_connection(app=current_project.app)
        context = {
          'project': current_project,
          'db': current_project.db,
          'app': current_project.app,
          'celery': current_project.celery
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
      elif args.command == 'worker':
        if args.verbose_help:
          current_project.celery.worker_main(['worker', '-h'])
        else:
          hostname = current_project.NAME.lower().replace(' ', '_')
          options = ['worker', '--hostname=%s.%s' % (args.name, hostname)]
          if args.queues:
            options.append('--queues=%s' % args.queues)
          if args.beat:
            options.extend([
              '--beat',
              '--schedule=%s/dev.sch' % current_project.CELERY_SCHEDULE_FOLDER
            ])
          if args.raw:
            options.extend(args.raw)
          current_project.celery.worker_main(options)
      elif args.command == 'flower':
        if args.verbose_help:
          current_project.celery.start(['celery', 'flower', '--help'])
        else:
          options = ['celery', 'flower', '--port=%s' % args.port]
          if args.raw:
            options.extend(args.raw)
          current_project.celery.start(options)

if __name__ == '__main__':
  main()
