View tracker
============

In this example we build a simple page view tracker:

Each time a page in our application will be visited, we would like to
store the visit in a local SQLite database. And since this is for testing
purposes, let's imagine we are also interested in seeing what queries are
issued by the database engine. The resulting configuration file is available
in ``conf.yaml``.

Our application consists of a single Flask view and a model corresponding
to page visits. All the code is in ``app.py``.

To run:

.. code:: bash

  $ kit server conf.yaml
