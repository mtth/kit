#!/usr/bin/env python

"""To load templates."""

from argparse import ArgumentParser, REMAINDER
from code import interact
from distutils.dir_util import copy_tree
from os import mkdir
from os.path import abspath, dirname, join
from shutil import copy
from sys import path

from flasker.project import Project, ProjectImportError

parser = ArgumentParser('flasker')
parser.add_argument('-c', '--conf',
  dest='conf',
  default='project.cfg',
  help='path to configuration file [%(default)s]'
)
subparsers = parser.add_subparsers(
  title='available commands',
  dest='command',
#  description='valid subcommands',
#  help='some text help to go here'
)

# New

new_parser = subparsers.add_parser('new', help='start new project')

new_parser.add_argument('-a', '--app',
  action='store_true',
  help='include basic bootstrap app template'
)
new_parser.add_argument('-n', '--name',
  default='project.cfg',
  help='name of the new config file [%(default)s]'
)
new_parser.add_argument('config',
  choices=['dev', 'prod'],
  help='the type of config to create'
)

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
  if args.command == 'new':
    src = dirname(__file__)
    copy(join(src, 'examples', '%s.cfg' % args.config), args.name)
    print 'Project configuration file created.'
    if args.app:
      copy_tree(join(src, 'data'), '.')
      print 'Bootstrap app folder created.'
    print 'All set!'
  else:
    path.append(abspath(dirname(args.conf))) # necessary for reloader to work
    try:
      pj = Project(args.conf)
    except ProjectImportError as e:
      print e
      return
    else:
      pj.make()
      if args.command == 'server':
        host = '127.0.0.1' if args.restrict else '0.0.0.0'
        pj.db.create_connection(app=pj.app)
        pj.app.run(host=host, port=args.port, debug=args.debug)
      elif args.command == 'shell':
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
      elif args.command == 'worker':
        if args.verbose_help:
          pj.celery.worker_main(['worker', '-h'])
        else:
          hostname = pj.config['PROJECT']['SHORTNAME']
          options = ['worker', '--hostname=%s.%s' % (args.name, hostname)]
          if args.queues:
            options.append('--queues=%s' % args.queues)
          if args.beat:
            options.append('--beat')
          if args.raw:
            options.extend(args.raw)
          pj.celery.worker_main(options)
      elif args.command == 'flower':
        if args.verbose_help:
          pj.celery.start(['celery', 'flower', '--help'])
        else:
          options = ['celery', 'flower', '--port=%s' % args.port]
          if args.raw:
            options.extend(args.raw)
          pj.celery.start(options)

if __name__ == '__main__':
  main()
