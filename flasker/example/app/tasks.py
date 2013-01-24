#!/usr/bin/env python

from flasker import current_project
from logging import getLogger

logger = getLogger(__name__)

celery = current_project.celery

@celery.task
def add():
  logger.warn('ADDING')
  return 3

