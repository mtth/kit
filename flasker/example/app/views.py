#!/usr/bin/env python

from flask import jsonify, render_template
from flask.ext.login import login_required
from flasker import current_project
from logging import getLogger

from . import tasks

logger = getLogger(__name__)

app = current_project.app

@app.route('/')
@login_required
def index():
  logger.warn('INDEX')
  return render_template('index.html')

@app.route('/add')
def add():
  logger.warn('VIEW ADDING')
  tasks.add.delay() 
  return jsonify({'success': 'yes!'})

