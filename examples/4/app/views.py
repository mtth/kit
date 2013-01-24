#!/usr/bin/env python

from flask import jsonify
from flasker import current_project
from logging import getLogger

logger = getLogger(__name__)

app = current_project.app

@app.route('/')
def index():
  logger.warn('HIIIII')
  return jsonify({'success': 'yes!'})
