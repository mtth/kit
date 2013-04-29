Twitter poller
==============

Kit example using Flask, Celery, and SQAlchemy.

This example implements a background API poller to study how tweets get
retweeted. Retweet counts are polled every 10 minutes from the Twitter API,
stored in a database and can then be analyzed offline.

The worker can be started with (the ``-B`` flag activates the celerybeat
scheduler):

.. code:: bash

  $ kit worker conf.yaml -- -B

As usual, the server can be started with:

.. code:: bash

  $ kit server conf.yaml
