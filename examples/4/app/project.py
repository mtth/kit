#!/usr/bin/env python

from flasker import BaseProject

class Project(BaseProject):

  NAME = 'Hi'
  MODULES = ['views']

project = Project()
