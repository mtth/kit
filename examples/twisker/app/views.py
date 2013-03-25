#!/usr/bin/env python

from dateutil.parser import parse
from flask import abort, jsonify, request
from flasker import current_project as pj
from flasker.ext import API
from twitter import Api

import app.models as m
import app.test as t

app = pj.flask

client = Api()

@pj.before_startup
def preproc(project):
  project.r = t.request

def load_user(user_handle):
  # for tweet in pj.session.query(m.Tweet):
  #   print 'DELETEING %r' % tweet
  #   pj.session.delete(tweet)
  # pj.session.commit()
  u = client.GetUser(user_handle)
  user, flag = m.User.retrieve(id=u.id)
  if flag:
    columns = ['id', 'name', 'screen_name', 'friends_count', 'followers_count']
    for col in columns:
      setattr(user, col, getattr(u, col))
    print 'ADDING USER TO SESSION'
  return user

def load_tweets(user):
  ts = client.GetUserTimeline(
    user.screen_name,
    page=int(page or 0),
    trim_user=True,
  )
  user_id = user.id
  print 'TWEETS LOADED'
  for t in ts:
    print 'DOING TWEET'
    columns = ['text', 'retweet_count', 'source']
    # pj.session.remove()
    # tweet = pj.session.query(m.Tweet).get(t.id)
    # tweet = m.Tweet.q.get(t.id)
    # pj.session.remove()
    # if not tweet:
    #   tweet = m.Tweet(id=t.id, user_id=user_id)
    tu, flag = m.TweetUser.retrieve(user_id=user.id, tweet_id=t.id)
    tweet, flag = m.Tweet.retrieve(id=t.id)
    if flag:
      print 'NEW TWEET, LOADING ATTRIBUTES'
      tweet.created_at = parse(t.created_at)
      for col in columns:
        setattr(tweet, col, getattr(t, col))
      user.tweets.append(tweet)
      pj.session.add(tweet)
  return jsonify(user.to_json())

api = API(pj)

class User(api.View):

  __model__ = m.User

  methods = ['GET', 'POST']
  subviews = ['tweets']

  def post(self):
    user_handle = request.form.get('handle')
    if user_handle:
      user = load_user(user_handle)
      return jsonify(user.to_json())
    return abort(404), 404

  def put(self, id=None):
    user = m.User.q.get(id)

class TweetUser(api.View):

  __model__ = m.TweetUser

