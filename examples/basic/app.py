#!/usr/bin/env python

from flasker import current_project as pj

@pj.flask.route('/')
def index():
  return 'Hello World!'

