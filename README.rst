Flasker
=======

A configurable, lightweight framework that integrates Flask_, SQLAlchemy_ and
Celery_.

- What Flasker is!
  
    - A one stop ``.cfg`` configuration file for Flask, Celery and the
      SQLAlchemy engine.
    
    - A simple pattern to organize your project via the
      ``flasker.current_project`` proxy (cf. `Quickstart`_).

    - A command line tool from where you can create new projects, launch the
      Flask buit in Werkzeug_ server, start Celery workers and the Flower_
      tool, and run a shell in the current project context.

- What Flasker isn't?

    - A simplified version of Flask, Celery, and SQLAlchemy. Some knowledge of these
      frameworks is therefore required. 

Flasker is under development. You can find the latest version on GitHub_ and
read the documentation on `GitHub pages`_.


Installation
------------

Using ``pip``:

.. code:: bash

  $ pip install flasker

Using ``easy_install``:

.. code:: bash

   $ easy_install flasker


Quickstart
----------

This short guide will show you how to get an application combining Flask,
Celery and SQLAlchemy running in seconds (the code is available on GitHub in
``examples/basic/``).

We start from an empty directory ``project/`` and inside we create a basic
configuration file ``project.cfg``:

.. code:: cfg

  [PROJECT]
  NAME = My Flasker Project
  MODULES = app

The ``MODULES`` option contains the list of python modules which will be
included in the project. Inside each of these modules you can use the
``flasker.current_project`` proxy to get access to the current project
instance (which gives access to the configured Flask application, the Celery
application and the SQLAlchemy database session registry). For now we only
add a single module ``app``:

.. code:: python

   from flask import jsonify
   from flasker import current_project

   flask_app = current_project.flask    # Flask app
   celery_app = current_project.celery  # Celery app
   session = current_project.session    # SQLAlchemy scoped session maker

   # for this simple example we will only use flask_app

   @flask_app.route('/')
   def index():
    return jsonify({'message': 'Welcome!'})

Finally, we save this file to ``project/app.py`` and we're all set! To start
the server, we run (from the command line in the ``project/`` directory):

.. code:: bash

   $ flasker server 
   * Running on http://0.0.0.0:5000/

We can check that our server is running for example using Requests_ (if we
navigate to the same URL in the browser, we would get similarly exciting
results):

.. code:: python

   In [1]: import requests
   In [2]: requests.get('http://localhost:5000/').json()
   Out[2]: {u'message': u'Welcome!'}

Right now, the Flask app is running using the default configuration. We can
change this by adding configuration options to the ``project.cfg`` file. For
example, we will enable testing and debugging for easier bug tracking. At the
same time, we tell our project to store the database on disk (instead of the
default in memory SQLite store used by Flasker). Our configuration file now
looks like this:

.. code:: cfg

  [PROJECT]
  NAME = My Flasker Project
  MODULES = app
  [ENGINE]
  URL = sqlite:///db.sqlite
  [FLASK]
  DEBUG = true
  TESTING = true

Likewise, we could configure celery by adding options to a section ``CELERY``.
Any valid Flask, Celery or engine configuration option can go in their
respective section. There are also a few other options available which are
detailed in the project documentation.


Next steps
----------

Under the hood, on project startup, Flasker configures Flask, Celery and the
database engine and imports all the modules declared in ``MODULES`` (the
configuration file's directory is appended to the python path, so any module
in our ``project/`` directory will be accessible).

There are two ways to start the project.

* The simplest is to use the flasker console tool:

  .. code:: bash

    $ flasker -h

  This will list all commands now available for that project:

  - ``server`` to run the Werkzeug app server
  - ``worker`` to start a worker for the Celery backend
  - ``flower`` to run the Flower worker management app
  - ``shell`` to start a shell in the current project context (using IPython_ 
    if it is available)

  Extra help is available for each command by typing:

  .. code:: bash

    $ flasker <command> -h

* Or you can load the project manually:

  This is useful for example if you are using a separate WSGI server or working
  from an IPython Notebook.

  .. code:: python

     from flasker import Project

     project = Project('path/to/default.cfg')

To read more on how to user Flasker and configure your Flasker project, refer
to the documentation on `GitHub pages`_.


Extensions
----------

Flasker also comes with extensions for commonly needed functionalities:

- Expanded SQLAlchemy base and queries
- ReSTful API
- Authentication via OpenID *(still alpha)*


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
.. _Wiki: https://github.com/mtth/flasker/wiki
.. _GitHub pages: http://mtth.github.com/flasker
.. _GitHub: http://github.com/mtth/flasker
.. _IPython: http://ipython.org/
.. _Werkzeug: http://werkzeug.pocoo.org/
.. _Requests: http://docs.python-requests.org/en/latest/

