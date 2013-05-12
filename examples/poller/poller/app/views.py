#!/usr/bin/env python

from flask import render_template
from kit import Flask, get_config

app = Flask(__name__)

@app.route('/')
def index():
  handles = ', '.join(map(str, get_config()['twitter']['handles']))
  return render_template('index.html', handle=handles)
