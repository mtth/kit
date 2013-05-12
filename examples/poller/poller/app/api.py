#!/usr/bin/env python

from kit import Flask
from kit.ext import API

from ..models import orm

app = Flask(__name__)
api = API(app)


class UserView(api.View):

  __model__ = orm.models['User']

  subviews = True


class TweetView(api.View):

  __model__ = orm.models['Tweet']

  subviews = ['retweet_counts']


class RetweetCountView(api.View):

  __model__ = orm.models['RetweetCount']


api.register(app)
