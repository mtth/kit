Twitter poller
==============

Kit example using Celery, and SQAlchemy.

This example implements a background API poller to study how tweets get
retweeted. Retweet counts are stored in a database and can then be analyzed
offline.

The worker can be started with:

.. code:: bash

  $ kit worker poller -r -B

This application uses the celerybeat scheduler to automatically run tasks
on scheduled intervals (activated via the ``-B`` flag).

