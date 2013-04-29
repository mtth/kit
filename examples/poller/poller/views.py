#!/usr/bin/env python

from kit import Flask

app = Flask(__name__)

@app.route('/')
def index():
  return 'This is high tooo again!!'
