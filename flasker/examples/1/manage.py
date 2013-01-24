#!/usr/bin/env python

from flasker import ProjectManager

from app.project import project

pm = ProjectManager(project)

if __name__ == '__main__':
  pm.run()
