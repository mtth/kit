#!/usr/bin/env python

from flask import jsonify
from flasker import current_project

app = current_project.app

@app.route('/')
def index():
  return jsonify({'success': 'yes!'})
