#!/usr/bin/env python

from flask import render_template
from flask.ext.login import login_required

import core

app = core.fk.get_app()

@app.route('/')
@login_required
def index():
  return render_template('index.html')
