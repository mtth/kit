Kit
===

A configurable, lightweight framework that integrates Flask_, SQLAlchemy_, and
Celery_.

* Consolidate your configuration options into one YAML file:

  .. code:: yaml

    flask:
      name: 'app'
      config:
        debug: yes
        testing: yes
    celery:
      config:
        broker_url: 'redis://'
    sqlalchemy:
      url: 'mysql://...'
      engine:
        pool_recycle: 3600

* Run your project from the command line:

  * Start the Werkzeug_ webserver:

    .. code:: bash

      $ kit server -d -p 5050
       * Running on http://0.0.0.0:5050/
       * Restarting with reloader

  * Start a shell in your project's context (using IPython_ if available):

    .. code:: bash

      $ kit shell
      ...
      In [1]: kit.session
      Out[1]: <sqlalchemy.orm.scoping.scoped_session at 0x10b2dccd0>
      In [2]:

  * Start Celery workers:

    .. code:: bash

      $ kit worker my_project

  * Start the Flower_ monitor tool:

    .. code:: bash

      $ kit flower


Kit handles all the Flask, Celery, and SQLAlchemy setup. It only creates those
you need for your application and makes sure database connections are correctly
handled under the hood. Check out the ``examples/`` folder for a few sample
applications.

*Kit is under development.*


Installation
------------

.. code:: bash

   $ pip install kit

If you don't already have Flask, Celery, and SQLAlchemy installed you might
want:

.. code:: bash

   $ pip install flask celery sqlalchemy kit


Quickstart
----------

There are two ways you can use Kit.

* By specifying a configuration path directly:

  .. code:: python

    from kit import Kit

    kit = Kit('/path/to/conf.yaml')

    flask_app = kit.flask     # the configured Flask application
    celery_app = kit.celery   # the configured Celery application
    session = kit.session     # the configured SQLAlchemy scoped session maker

    # Here we will only use flask_app

    @flask_app.route('/')
    def index():
      return 'Hello world!'

    if __name__ == '__main__':
      flask_app.run()

* By using the ``modules`` configuration option:

  .. code:: yaml

    modules: ['app.models', 'app.tasks']
    ...

  Inside each of these modules, any ``Kit`` instantiation without a path
  argument will return a copy of the same kit. You can then use the command
  line tool to run different components of your project.

  Alternatively, you can pass ``load_modules=True`` when instantiating the
  ``Kit``: ``kit = Kit('/path/to/conf.yaml', load_modules=True)``.  This can be
  useful to to run the application on a different server or load data in an
  IPython notebook.

You can also combine both these methods for more complex results.


.. _Bootstrap: http://twitter.github.com/bootstrap/index.html
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
