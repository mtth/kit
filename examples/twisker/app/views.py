#!/usr/bin/env python

from flasker import current_project as pj
from flasker.ext import API

import app.models as m


api = API(pj)


class User(api.View):

  __model__ = m.User

  subviews = ['tweets']

  def get(self, **kwargs):
    user_handle = kwargs.get('handle', None)
    if user_handle:
      user = m.User.q.get(user_handle)
      if not user:
        user = m.User.import_new_user(user_handle)
    return super(User, self).get(**kwargs)


class Tweet(api.View):

  __model__ = m.Tweet


@pj.celery.periodic_task(run_every=10)
def update():
  for user in m.User.q:
    user.import_new_tweets()

