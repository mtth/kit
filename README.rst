Kit
===

A configurable, lightweight framework that integrates Flask_, SQLAlchemy_, and
Celery_.

  * Configure all your applications and sessions from one file (cf
    Quickstart_ for an example).

  * Run your project from the command line: Start the Werkzeug_ webserver,
    start Celery workers, start a shell in your project's context (using
    IPython_ if available), and start the Flower_ monitor using the ``kit``
    command line tool.

  * No more complicated import schemes: ``kit.Flask`` and ``kit.Celery`` always
    return the correct (and configured) application corresponding to the
    module.

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


Quickstart
----------

Sample configuration file:

.. code:: yaml

  root: '..'
  modules: ['my_project.startup']
  flasks:
    - modules: ['my_project.app', 'my_project.app.views']
      kwargs:
        static_folder: 'st'
      config:
        debug: yes
        testing: yes
    - modules: ['my_project.api']
  celeries:
    - modules: ['my_project.tasks']
      config:
        broker_url: 'redis://'
  sessions:
    db:
      url: 'mysql://...'
      engine:
        pool_recycle: 3600
      options:
        commit: yes
        raise: no


The following configuration options are available:

* ``root``: project root, will be added to your python path. Useful if your
  configuration files are in a subdirectory of your project (defaults to
  ``'.'``)

* ``modules``: list of modules to import (and that don't belong to an
  application).

* ``flasks``: list of Flask application settings. Each item has the following
  keys available:

  * ``modules``: list of modules where this application is used. Inside each
    of these modules, you can use ``kit.Flask`` to recover this
    configured application. The application's name will be automatically
    generated from this list of modules.
  * ``kwargs``: dictionary of keyword arguments passed to the ``flask.Flask``
    constructor.
  * ``config``: dictionary of configuration options used to configure the
    application. Names are case insensitive so no need to uppercase them.

* ``celeries``: list of Celery application settings. Each item has the
  following keys available:

  * ``modules``: list of modules where this application is used. Inside each
    of these modules, you can use ``kit.Celery`` to recover this
    configured application. The application's name will be automatically
    generated from this list of modules.
  * ``kwargs``: dictionary of keyword arguments passed to the
    ``celery.Celery`` constructor.
  * ``config``: dictionary of configuration options used to configure the
    application. Names are case insensitive so no need to uppercase them.

* ``sessions``: dictionary of sessions. The key is the session name (used
  as argument to ``kit.get_session``). Each item has the following
  settings available:

  * ``url``: the database url (defaults to ``sqlite://``)
  * ``kwargs``: dictionary of keyword arguments to pass to
    ``sqlalchemy.orm.sessionmaker``.
  * ``engine``: dictionary of keyword arguments to pass to the bound engine's
    constructor.
  * ``options``: there are currently two options available:

    * ``commit``: whether or not to commit the session after each request
      or task (defaults to ``False``).
    * ``raise``: whether or not to reraise any errors found during commit
      (defaults to ``True``).

Note that there can only be one application of each type (Flask or Celery) in
a given module. This shouldn't be too restrictive as it is arguably bad
practice to mix applications in a same module.


Next steps
----------

To instantiate an application outside of the command line tool (for example
to run it on a different WSGI server), you can specify a ``path`` argument
to the ``kit.Flask`` function. This will load the kit before returning
the application. The ``path`` argument is available on all other functions as
well (for example to allow model access from an IPython notebook).


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
