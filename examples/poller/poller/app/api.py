#!/usr/bin/env python

from kit import Flask
from kit.ext import API

from ..models import orm

app = Flask(__name__)
api = API(app)
models = orm.get_all_models()

class TweetView(api.View):

  __model__ = models['Tweet']

  subviews = ['retweet_counts']


class RetweetCountView(api.View):

  __model__ = models['RetweetCount']


api.register(app)
