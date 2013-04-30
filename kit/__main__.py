#!/usr/bin/env python

"""Kit: your friendly Flask, Celery, SQLAlchemy toolkit.

Usage:
  kit shell CONF
  kit server [-dlp PORT] CONF
  kit worker CONF [(-- [RAW] ...)]
  kit flower CONF [(-- [RAW] ...)]
  kit -h | --help | --version

Arguments:
  CONF                  Path to YAML configuration file.
  RAW                   Options to pass to the underlying command.

Options:
  -h --help             Show this screen.
  --version             Show version.
  -d --debug            Enable in browser debugging and autoreloading.
  -l --local            Only allow local connections to server.
  -p PORT --port=PORT   Port to run server on [default: 5000].
  
"""

from code import interact
from docopt import docopt
from kit import __version__, get_kit
from os import getenv, environ, sep
from os.path import abspath, basename, dirname, join, split, splitext
from re import findall


def run_shell(kit):
  """Start a shell in the context of the kit (using IPython if available)."""
  context = {
    'kit': kit,
  }
  try:
    import IPython
  except ImportError:
    interact(local=context)
  else:
    interactive_shell = IPython.frontend.terminal.embed.InteractiveShellEmbed()
    interactive_shell(local_ns=context)

def run_server(kit, local, port, debug):
  """Start a Werkzeug server for the Flask application."""
  host = '127.0.0.1' if local else '0.0.0.0'
  apps = len(kit.flasks)
  if not apps:
    print 'No Flask app found!'
    return
  elif apps == 1:
    app = kit.flasks[0]
  else:
    app_number = getenv('KIT_FLASK_APP', None)
    if not app_number:
      s = '%s Flask applications found:\n\n   # Name\n' % (apps, )
      s += '\n'.join(
        '%04s %s' % (index, flask_app.name)
        for index, flask_app in enumerate(kit.flasks)
      )
      s += '\n\nWhich # would you like to run? '
      app_number = raw_input(s)
      environ['KIT_FLASK_APP'] = app_number
    app = kit.flasks[int(app_number)]
  app.run(host=host, port=port, debug=debug, extra_files=[kit.path])

def run_worker(kit, raw):
  """Starts a celery worker.

  If no hostname is provided, one will be generated automatically using the
  configuration file path and kit project root. For example, the first two
  workers started for project root ``my_project`` and configuration ``default``
  will have respective hostnames:

  * w1.default.my_project
  * w2.default.my_project

  """
  if not len(kit.celeries):
    print 'No Celery app found!'
    return
  elif len(kit.celeries) == 1:
    app = kit.celeries[0]
  else:
    for index, flask_app in enumerate(kit.celeries):
      print '%02s %s' % (index, flask_app.name)
    app = kit.celeries[int(raw_input('Which app would you like to run? '))]
  name = app.main
  base_hostname = '%s.%s.%s' % (
    splitext(split(kit.path)[1])[0],
    name,
    basename(abspath(join(
      dirname(kit.path),
      kit.root.rstrip(sep)
    ))),
  )
  worker_pattern = r'w(\d+)\.%s' % (base_hostname, )
  kit_worker_names = [d.keys()[0] for d in app.control.ping()]
  worker_numbers = [
    findall(worker_pattern, worker_name) or ['0']
    for worker_name in kit_worker_names
  ]
  wkn = min(
    set(range(1, len(worker_numbers) + 2)) -
    set([int(n[0]) for n in worker_numbers] or [len(worker_numbers) + 2]) 
  )
  hostname = 'w%s.%s' % (wkn, base_hostname)
  options = ['worker', '--hostname=%s' % hostname] + raw
  app.worker_main(options)

def run_flower(kit, raw):
  """Start flower worker manager."""
  options = ['celery', 'flower'] + raw
  if not len(kit.celeries):
    print 'No Celery app found!'
  else:
    kit.celeries[0].start(options)

def main():
  """Command line parser."""
  arguments = docopt(__doc__, version=__version__)
  kit = get_kit(arguments['CONF'])
  if arguments['shell']:
    run_shell(kit)
  elif arguments['server']:
    run_server(
      kit,
      local=arguments['--local'],
      port=int(arguments['--port']),
      debug=arguments['--debug'],
    )
  elif arguments['worker']:
    run_worker(kit, raw=arguments['RAW'])
  elif arguments['flower']:
    run_flower(kit, raw=arguments['RAW'])

if __name__ == '__main__':
  main()
