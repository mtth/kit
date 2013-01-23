#!/usr/bin/env python

from flask import jsonify
from project import project

app = project.app

@app.route('/')
def index():
  return jsonify({'success': 'yes!'})
