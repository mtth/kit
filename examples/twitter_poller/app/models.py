#!/usr/bin/env python

"""SQLAlchemy models."""

from datetime import datetime
from kit import Kit
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Unicode
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship

kit = Kit()

Base = declarative_base()


class Tweet(Base):

  __tablename__ = 'tweets'

  id = Column(Integer, primary_key=True)
  text = Column(Unicode(140))
  created_at = Column(DateTime(timezone=False))


class RetweetCount(Base):

  __tablename__ = 'retweet_counts'

  id = Column(Integer, primary_key=True)
  date = Column(DateTime, default=datetime.now)
  tweet_id = Column(ForeignKey('tweets.id'))
  retweet_count = Column(Integer)

  tweet = relationship(
    'Tweet',
    backref=backref('retweet_counts', lazy='dynamic')
  )


Base.metadata.create_all(kit.session.get_bind())

