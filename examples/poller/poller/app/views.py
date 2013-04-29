#!/usr/bin/env python

from flask import render_template
from kit import Flask, get_config

app = Flask(__name__)

@app.route('/')
def index():
  handle = get_config()['twitter']['user_handle']
  return render_template('index.html', handle=handle)
