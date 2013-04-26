#!/usr/bin/env python

"""SQLAlchemy models."""

from datetime import datetime
from kit import get_sessions
from kit.ext.orm import ORM
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Unicode

session = get_sessions()[0]
orm = ORM(session)

class Tweet(orm.Model):

  _cache = None
  id = Column(Integer, primary_key=True)
  text = Column(Unicode(140))
  created_at = Column(DateTime(timezone=False))


class RetweetCount(orm.Model):

  _cache = None
  id = Column(Integer, primary_key=True)
  date = Column(DateTime, default=datetime.now)
  tweet_id = Column(ForeignKey('tweets.id'))
  retweet_count = Column(Integer)

  tweet = orm.relationship(
    'Tweet',
    backref=orm.backref('retweet_counts', lazy='dynamic')
  )

orm.create_all()
