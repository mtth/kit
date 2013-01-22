#!/usr/bin/env python

from flask import render_template

import core

app = core.fk.get_app()

@app.route('/')
def index():
  return render_template('index.html')
