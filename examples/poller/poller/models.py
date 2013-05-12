#!/usr/bin/env python

"""SQLAlchemy models."""

from datetime import datetime
from kit import get_session
from kit.ext.orm import ORM
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Unicode, desc

session = get_session('db')
orm = ORM(session)


class User(orm.Model):

  handle = Column(Unicode(36), primary_key=True)

  @property
  def latest_tweet(self):
    latest_tweet = self.tweets.first()
    if latest_tweet:
      return latest_tweet.to_json()

  @property
  def total_saved_tweets(self):
    return self.tweets.fast_count()

  @property
  def average_retweet_count(self):
    n_tweets = self.total_saved_tweets
    if n_tweets:
      total = sum(tweet.current_retweet_count for tweet in self.tweets)
      return float(total) / n_tweets


class Tweet(orm.Model):

  id = Column(Integer, primary_key=True)
  date = Column(DateTime, default=datetime.now)
  user_handle = Column(ForeignKey('users.handle'))
  text = Column(Unicode(140))
  created_at = Column(DateTime(timezone=False))

  user = orm.relationship(
    'User',
    backref=orm.backref(
      'tweets',
      lazy='dynamic',
      order_by=desc(created_at),
    )
  )

  @property
  def age(self):
    return datetime.now() - self.date

  @property
  def current_retweet_count(self):
    latest_count = self.retweet_counts.first()
    if latest_count:
      return latest_count.retweet_count


class RetweetCount(orm.Model):

  id = Column(Integer, primary_key=True)
  date = Column(DateTime, default=datetime.now)
  tweet_id = Column(ForeignKey('tweets.id'))
  retweet_count = Column(Integer)

  tweet = orm.relationship(
    'Tweet',
    backref=orm.backref(
      'retweet_counts',
      lazy='dynamic',
      order_by=desc(date),
    )
  )

  @property
  def age(self):
    return self.date - self.tweet.date


orm.create_all()
