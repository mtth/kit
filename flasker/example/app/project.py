#!/usr/bin/env python

from flasker import BaseProject

class Project(BaseProject):

  NAME = 'My first Flasker project'
  MODULES = ['views', 'tasks']
  OAUTH_GOOGLE_CLIENT = 'hi'

project = Project()
