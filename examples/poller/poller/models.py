#!/usr/bin/env python

"""SQLAlchemy models."""

from datetime import datetime
from kit import get_session
from kit.ext.orm import ORM
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Unicode

session = get_session('db')
orm = ORM(session)


class User(orm.Model):

  handle = Column(Unicode(36), primary_key=True)


class Tweet(orm.Model):

  id = Column(Integer, primary_key=True)
  user_handle = Column(ForeignKey('users.handle'))
  text = Column(Unicode(140))
  created_at = Column(DateTime(timezone=False))

  user = orm.relationship(
    'User',
    backref=orm.backref('tweets', lazy='dynamic')
  )


class RetweetCount(orm.Model):

  id = Column(Integer, primary_key=True)
  date = Column(DateTime, default=datetime.now)
  tweet_id = Column(ForeignKey('tweets.id'))
  retweet_count = Column(Integer)

  tweet = orm.relationship(
    'Tweet',
    backref=orm.backref('retweet_counts', lazy='dynamic')
  )


orm.create_all()
