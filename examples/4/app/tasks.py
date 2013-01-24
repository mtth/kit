#!/usr/bin/env python

from flasker import current_project
from logging import getLogger

logger = getLogger(__name__)

celery = current_project.celery
db = current_project.db

@celery.task
def add():
  logger.warn('ADDING')
  return 3

print 'TASKS'
  
