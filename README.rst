Kit
===

A configurable, lightweight framework that integrates Flask_, SQLAlchemy_, and
Celery_.

  * Configure all your applications and sessions from one file (cf `Sample
    configuration file`_ for an example).

  * Run your project from the command line: Start the Werkzeug_ webserver,
    start Celery workers, start a shell in your project's context (using
    IPython_ if available), and start the Flower_ monitor tool.

  * No more complicated and sometimes circular, import schemes: ``kit.Flask``
    and ``kit.Celery`` always return the correct (and configured) application
    corresponding to the module.

  * Kit makes sure database connections are correctly handled (e.g. removed
    after each request and task) under the hood. You can configure this
    behavior via the ``kit.teardown_handler`` decorator.

Check out the ``examples/`` folder for a few sample applications or read the
full documentation on `GitHub pages`_.

*Kit is under development.*


Installation
------------

.. code:: bash

   $ pip install kit


Sample configuration file
-------------------------

.. code:: yaml

  flasks:
    - modules: ['app', 'app.views']
      config:
        debug: yes
        testing: yes
    - modules: ['api']
  celeries:
    - modules: ['tasks']
      config:
        broker_url: 'redis://'
  sessions:
    db:
      url: 'mysql://...'
      engine:
        pool_recycle: 3600


.. _Flask: http://flask.pocoo.org/docs/api/
.. _Flask-Script: http://flask-script.readthedocs.org/en/latest/
.. _Flask-Login: http://packages.python.org/Flask-Login/
.. _Flask-Restless: https://flask-restless.readthedocs.org/en/latest/
.. _Jinja: http://jinja.pocoo.org/docs/
.. _Celery: http://docs.celeryproject.org/en/latest/index.html
.. _Flower: https://github.com/mher/flower
.. _Datatables: http://datatables.net/examples/
.. _SQLAlchemy: http://docs.sqlalchemy.org/en/rel_0_7/orm/tutorial.html
.. _MySQL: http://dev.mysql.com/doc/
.. _Google OAuth 2: https://developers.google.com/accounts/docs/OAuth2
.. _Google API console: https://code.google.com/apis/console
.. _jQuery: http://jquery.com/
.. _jQuery UI: http://jqueryui.com/
.. _Backbone-Relational: https://github.com/PaulUithol/Backbone-relational
.. _FlaskRESTful: http://flask-restful.readthedocs.org/en/latest/index.html
.. _GitHub pages: http://mtth.github.com/kit
.. _GitHub: http://github.com/mtth/kit
.. _IPython: http://ipython.org/
.. _Werkzeug: http://werkzeug.pocoo.org/
.. _Requests: http://docs.python-requests.org/en/latest/
.. _examples/view_tracker: https://github.com/mtth/kit/tree/master/examples/view_tracker
.. _YAML: http://www.yaml.org/
.. _Pandas: http://pandas.pydata.org/
