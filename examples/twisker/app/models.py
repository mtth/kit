#!/usr/bin/env python

from flasker import current_project as pj
from flasker.ext import ORM
from sqlalchemy import Column, DateTime, Unicode, Integer, ForeignKey
from twitter import Api

orm = ORM(pj)
Model = orm.Model
relationship = orm.relationship
backref = orm.backref

api = Api()

class User(Model):

  id = Column(Integer, primary_key=True)
  name = Column(Unicode(128))
  screen_name = Column(Unicode(32))
  friends_count = Column(Integer)
  followers_count = Column(Integer)


class Tweet(Model):

  id = Column(Integer, primary_key=True)
  user_id = Column(ForeignKey('users.id'))
  text = Column(Unicode(140))
  retweet_count = Column(Integer)
  source = Column(Unicode(32))
  created_at = Column(DateTime)

  user = relationship(
    'User',
    backref=backref('tweets')
  )

class TweetUser(Model):

  user_id = Column(Integer, primary_key=True)
  tweet_id = Column(Integer, primary_key=True)

