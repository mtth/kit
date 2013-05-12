#!/usr/bin/env python

"""Celery tasks."""

from dateutil.parser import parse
from kit import Celery, get_config
from twitter import Api

from .models import RetweetCount, Tweet, User

celery = Celery(__name__)

# Twitter API client
client = Api()

@celery.periodic_task(run_every=1800)
def get_user_timeline():
  """Retrieve a user's most recent tweets and update retweet counts for each.

  This function runs automatically every 10 minutes in a Celery worker.

  """
  for user in User.q:
    tweet_infos = client.GetUserTimeline(
      user.handle,   # the user we are interested in
      count=200,                            # number of recent tweets to retrieve
      trim_user=True                        # not interested in who retweeted
    )
    for tweet_info in tweet_infos:
      tweet, flag = Tweet.retrieve(
        from_key=True,
        flush_if_new=True,
        **{
          'id': tweet_info.id,
          'text': tweet_info.text,
          'created_at': parse(tweet_info.created_at),
          'user_handle': user.handle,
        }
      )
      # we add a new retweet count for this tweet
      tweet.retweet_counts.append(
        RetweetCount(retweet_count=tweet_info.retweet_count)
      )


