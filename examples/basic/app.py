#!/usr/bin/env python

from flask import jsonify
from flasker import current_project as pj

@pj.flask.route('/')
def index():
  return jsonify({'message': 'Welcome'})

