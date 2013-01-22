#!/usr/bin/env python

from flask import render_template
from flasker import App, Manager

app = App('Example 1')
manager = Manager(app)

@app.route('/')
def index():
  return render_template('index.html')

if __name__ == '__main__':
  manager.run()
