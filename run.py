#!/usr/bin/env python

from app import make_app

app = make_app(debug=True)

app.run('0.0.0.0', debug=True)
