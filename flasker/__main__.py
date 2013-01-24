#!/usr/bin/env python

"""To load templates."""

from distutils.dir_util import copy_tree
from flask.ext.script import prompt_bool
from os import mkdir
from os.path import abspath, dirname, join
from shutil import move

def main():
  if prompt_bool('Create a new project in this folder'):
    copy_example(1)

def copy_templates():
  src = join(dirname(__file__), 'examples', 'templates')
  copy_tree(src, join('app', 'templates'))

def copy_example(version):
  src = join(dirname(__file__), 'examples', str(version))
  copy_tree(src, 'app')
  for folder in ['celery', 'db', 'logs', 'static']:
    mkdir(join('app', folder))
  move(join('app', 'manage.py'), 'manage.py')
  copy_templates()

if __name__ == '__main__':
  main()
