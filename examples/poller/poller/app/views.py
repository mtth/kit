#!/usr/bin/env python

from flask import render_template
from kit import Flask

app = Flask(__name__)

@app.route('/')
def index():
  return render_template('index.html', item='world')
