#!/usr/bin/env python

"""To load templates."""

from distutils.dir_util import copy_tree
from flask.ext.script import prompt, prompt_choices
from os.path import abspath

def main():
  choice = int(prompt_choices(
    'What would you like to do',
    [
      ('1', 'Load example 1'),
      ('2', 'Load example 2'),
      ('3', 'Load example 3'),
      ('0', 'Exit'),
    ],
    resolve=lambda e: str(e)
  ))
  if choice > 0:
    directory = abspath(prompt('In which directory', default='.'))
    print 'Copying example %s...' % choice
    copy_tree()

if __name__ == '__main__':
  main()
