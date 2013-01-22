#!/usr/bin/env python

from flasker import Flasker

fk = Flasker('Example 1')

app = fk.get_app()

@app.route('/')
def index():
  return "Welcome!"

if __name__ == '__main__':
  fk.run()
