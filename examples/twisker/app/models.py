#!/usr/bin/env python

from dateutil.parser import parse
from flasker import current_project as pj
from flasker.ext import ORM
from sqlalchemy import Column, DateTime, Unicode, Integer, ForeignKey
from twitter import Api


# twitter API client
client = Api()

# ORM extension
orm = ORM(pj)


class User(orm.Model):

  handle = Column(Unicode(32), primary_key=True)
  name = Column(Unicode(128))
  friends_count = Column(Integer)
  followers_count = Column(Integer)

  @classmethod
  def import_new_user(cls, handle):
    u = client.GetUser(handle)
    user, flag = cls.retrieve(
      use_key=True,
      **{
        'handle': u.screen_name,
        'name': u.name,
        'friends_count': u.friends_count,
        'followers_count': u.followers_count,
      }
    )
    user.import_new_tweets()
    return user

  def import_new_tweets(self):
    ts = client.GetUserTimeline(
      self.handle,
      count=200,
      trim_user=True,
    )
    new_tweets = []
    for t in ts:
      tweet, flag = Tweet.retrieve(
        use_key=True,
        **{
          'id': t.id,
          'text': t.text,
          'retweet_count': t.retweet_count,
          'source': t.source,
          'user': self,
          'created_at': parse(t.created_at),
        }
      )
      if flag:
        new_tweets.append(tweet)
    return new_tweets


class Tweet(orm.Model):

  id = Column(Integer, primary_key=True)
  user_handle = Column(ForeignKey('users.handle'))
  text = Column(Unicode(140))
  retweet_count = Column(Integer)
  source = Column(Unicode(32))
  created_at = Column(DateTime)

  user = orm.relationship(
    'User',
    backref=orm.backref('tweets', lazy='dynamic')
  )


