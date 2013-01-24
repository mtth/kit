#!/usr/bin/env python

from flasker import BaseProject

class Project(BaseProject):

  NAME = 'My Project'
  MODULES = ['app.views']

project = Project()
