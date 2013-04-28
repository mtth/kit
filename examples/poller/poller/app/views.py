#!/usr/bin/env python

from flask import render_template
from kit import Flask
from kit.util import make_view

app = Flask(__name__)

@app.route('/')
def index():
  return render_template('index.html', item='world!!!!')

View = make_view(app)

class Hello(View):

  rules = {
    '/hello': ['GET'],
    '/hello/<page>': ['GET']
  }

  def get(self, **kwargs):
    if not kwargs:
      return 'hello, no page specified'
    else:
      page = kwargs['page']
      return 'hello you are on page %s' % (page, )
