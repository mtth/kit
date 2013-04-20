#!/usr/bin/env python

"""Kit command line tool.

There are currently 4 commands available via the command tool, all
detailed below.

All commands accept an optional argument ``-c, --conf``
to indicate the path of the configuration file to use. If none is specified
kit will search in the current directory for possible matches. If a single
file ``.cfg`` file is found it will use it.

"""

from argparse import ArgumentParser, REMAINDER
from code import interact
from functools import wraps
from os import getenv, listdir
from os.path import abspath, splitext
from re import findall

from .base import Kit, KitImportError


def _kit_context(handler):
  """Create the kit context.

  Subparser handlers require the kit to be created before
  returning, this decorator handles this.

  """
  @wraps(handler)
  def wrapper(*args, **kwargs):
    parsed_args = args[0]
    try:
      conf_file = parsed_args.conf
      if not conf_file:
        if parsed_args.env:
          conf_file = getenv('KITPATH')
        else:
          paths = [fn for fn in listdir('.') if splitext(fn)[1] == '.yaml']
          if len(paths) == 0:
            print (
              'No configuration file found in current directory. '
              'Please enter a different path with the -c option.'
            )
            return
          elif len(paths) > 1:
            print (
              'Several configuration files found in current directory: %s. '
              'Please disambiguate with the -c option.'
            ) % ', '.join(paths)
            return
          else:
            conf_file = paths[0]
      kit = Kit(abspath(conf_file), load_modules=True)
    except KitImportError as e:
      print e
      return
    else:
      handler(kit, *args, **kwargs)
  return wrapper


# Parsers

# Main parser

parser = ArgumentParser('kit')

parser.add_argument('-c', '--conf',
  default='',
  help='path to configuration file (overrides over `-e`)'
)
parser.add_argument('-e', '--env',
  action='store_true',
  help='use environment KITPATH as configuration file path'
)
subparsers = parser.add_subparsers(
  title='available commands',
  dest='command',
)


# Server

server_parser = subparsers.add_parser('server', help='start server')

server_parser.add_argument('-r', '--restrict',
  action='store_true',
  help='disallow remote server connections'
)
server_parser.add_argument('-p', '--port',
  default=5000,
  type=int,
  help='listen on port [%(default)s]'
)
server_parser.add_argument('-d', '--debug',
  action='store_true',
  help='run in debug mode (autoreload and debugging)'
)

@_kit_context
def server_handler(kit, parsed_args):
  """Start a Werkzeug server for the Flask application::
  
    kit server ...

  The following options are available:

  * ``-r, --restrict`` to disallow remove server connections.
  * ``-p, --port`` to set the port on which to run the server (default to 
    ``5000``).
  * ``-d, --debug`` to run in debug mode (enables autoreloading and in-browser
    debugging).
  
  """
  host = '127.0.0.1' if parsed_args.restrict else '0.0.0.0'
  kit.flask.run(host=host, port=parsed_args.port, debug=parsed_args.debug)

server_parser.set_defaults(handler=server_handler)

# Shell

shell_parser = subparsers.add_parser('shell', help='start shell')

@_kit_context
def shell_handler(kit, parsed_args):
  """Start a shell in the context of the kit::

    kit shell ...

  The following global variables will be available:

  * ``pj``, an alias for the ``current_project``

  This will use IPython if it is available.
  
  """
  context = {'kit': kit}
  try:
    import IPython
  except ImportError:
    interact(local=context)
  else:
    sh = IPython.frontend.terminal.embed.InteractiveShellEmbed()
    sh(local_ns=context)

shell_parser.set_defaults(handler=shell_handler)

# Worker

worker_parser = subparsers.add_parser('worker', help='start worker')

worker_parser.add_argument('domain',
  help='worker domain name'
)
worker_parser.add_argument('-o', '--only-direct',
  action='store_true',
  help='only listen to direct queue'
)
worker_parser.add_argument('-v', '--verbose-help',
  action='store_true',
  help='show full help from celery worker'
)
worker_parser.add_argument('-r', '--raw',
  nargs=REMAINDER,
  help='raw options to pass through',
)

@_kit_context
def worker_handler(kit, parsed_args):
  """Starts a celery worker::

    kit worker ...

  The following options are available:

  * ``-o, --only-direct`` to have the worker only listen to its direct queue
    (this option requires the CELERY_WORKER_DIRECT to be set to ``True``).
  * ``-v, --verbose-help`` to show the worker help.
  * ``-r, --raw`` to pass arguments to the worker (any arguments after this
    option will be passed through).

  If no hostname is provided, one will be generated automatically using the
  project domain and subdomain and current worker count. For example, the first
  two workers started for project ``my_project`` and configuration ``default``
  will have respective hostnames:

  * w1.default.my_project
  * w2.default.my_project

  """
  domain = parsed_args.domain
  pj_worker_names = [d.keys()[0] for d in kit.celery.control.ping()]
  worker_pattern = r'w(\d+)\.%s' % (domain, )
  worker_numbers = [
    findall(worker_pattern, worker_name) or ['0']
    for worker_name in pj_worker_names
  ]
  wkn = min(
    set(range(1, len(worker_numbers) + 2)) -
    set([int(n[0]) for n in worker_numbers] or [len(worker_numbers) + 2]) 
  )
  if parsed_args.verbose_help:
    kit.celery.worker_main(['worker', '-h'])
  else:
    hostname = 'w%s.%s' % (wkn, domain)
    options = ['worker', '--hostname=%s' % hostname]
    if parsed_args.only_direct:
      options.append('--queues=%s.dq' % hostname)
    if parsed_args.raw:
      options.extend(parsed_args.raw)
    kit.celery.worker_main(options)

worker_parser.set_defaults(handler=worker_handler)

# Flower

flower_parser = subparsers.add_parser('flower', help='start flower')

flower_parser.add_argument('-p', '--port',
  default=5555,
  type=int,
  help='listen on port [%(default)s]'
)
flower_parser.add_argument('-v', '--verbose-help',
  action='store_true',
  help='show full help from celery flower'
)
flower_parser.add_argument('-r', '--raw',
  help='raw options to pass through',
  nargs=REMAINDER
)

@_kit_context
def flower_handler(kit, parsed_args):
  """Start flower worker manager::
    
    kit flower ...

  The following arguments are available:

  * ``-p, --port`` to set the port to run flower on (defaults to ``5555``).
  * ``-v, --verbose-help`` to show the flower help.
  * ``-r, --raw`` to pass arguments to flower (any arguments after this option
    will be passed through).
  
  """
  if parsed_args.verbose_help:
    kit.celery.start(['celery', 'flower', '--help'])
  else:
    options = ['celery', 'flower', '--port=%s' % parsed_args.port]
    if parsed_args.raw:
      options.extend(parsed_args.raw)
    kit.celery.start(options)

flower_parser.set_defaults(handler=flower_handler)
