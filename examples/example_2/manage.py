#!/usr/bin/env python

from flasker import Manager

from app import make_app

application = make_app()

manager = Manager(application)

if __name__ == '__main__':
  manager.run()
