#!/usr/bin/env python

"""Celery tasks."""

from dateutil.parser import parse
from kit import Kit
from twitter import Api

from .models import RetweetCount, Tweet

kit = Kit()

# Twitter API client
client = Api()

@kit.celery.periodic_task(run_every=600)
def get_user_timeline():
  """Retrieve a user's most recent tweets and update retweet counts for each.

  This function runs automatically every 10 minutes in a Celery worker.

  """
  tweet_infos = client.GetUserTimeline(
    kit.conf['twitter']['user_handle'],   # the user we are interested in
    count=200,                            # number of recent tweets to retrieve
    trim_user=True                        # not interested in who retweeted
  )
  for tweet_info in tweet_infos:
    # we try to find if this tweet already exists in the database
    tweet = kit.session.query(Tweet).get(tweet_info.id)
    if not tweet:
      # if it doesn't, we add it
      tweet = Tweet(
        id=tweet_info.id,
        text=tweet_info.text,
        created_at=parse(tweet_info.created_at),
      )
      kit.session.add(tweet)
    # we add a new retweet count for this tweet
    tweet.retweet_counts.append(
      RetweetCount(retweet_count=tweet_info.retweet_count)
    )


