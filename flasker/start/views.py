#!/usr/bin/env python

from flask import render_template
from flasker import flasker

app = flasker.get_app()

@app.route('/')
def index():
  return render_template('index.html')
