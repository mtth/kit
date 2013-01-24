#!/usr/bin/env python

"""To load templates."""

from argparse import ArgumentParser, REMAINDER
from distutils.dir_util import copy_tree
from flask.ext.script import prompt_bool
from imp import load_source
from os import mkdir
from os.path import abspath, dirname, join, sep
from sys import path

from project import current_project

parser = ArgumentParser('Flasker')

parser.add_argument(
  'command',
  nargs=REMAINDER
)

parser.add_argument(
  '-p',
  '--project',
  default='project.py',
  dest='project',
  help='Project module'
)

def start_project(version=1):
  """Start a new project"""
  src = join(dirname(__file__), 'examples')
  # copy project files
  copy_tree(join(src, str(version)), '.')
  # copy html files
  copy_tree(join(src, 'templates'), join('app', 'templates'))
  # create default directories
  mkdir(join('app', 'static'))
  for folder in ['celery', 'db', 'logs']:
    mkdir(folder)

if __name__ == '__main__':
  args = parser.parse_args()
  if args.command == ['new']:
    if prompt_bool('Start a new project'):
      start_project()
  else:
    try:
      path.append(abspath('.')) # necessary for reloader to work
      load_source('project', args.project)
    except ImportError, e:
      print e
    else:
      __import__('flasker.manager')
