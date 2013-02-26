#!/usr/bin/env python

from flask import redirect, render_template, url_for
from flasker import current_project

import tasks as t

app = current_project.flask

@app.route('/')
def index():
  """Splash page.
  
  Standard Flask code.
  
  """
  return render_template('index.html')

@app.route('/start_task')
def start_task():
  """Task hook.

  Accessing this URL will send the ``do_something`` task to the worker and
  redirect to the index (without waiting for the task to complete).

  """
  t.do_something.delay()
  return redirect(url_for('index'))
