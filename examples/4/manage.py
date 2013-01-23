#!/usr/bin/env python

from app import *
from flasker.manager import ProjectManager

pm = ProjectManager(project.project)

pm.run()
