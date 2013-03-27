Flasker
=======

A configurable, lightweight framework that integrates Flask_, SQLAlchemy_ and
Celery_.

- What Flasker is!
  
    - A one stop ``.cfg`` configuration file for Flask, Celery and SQLAlchemy.
    
    - A simple pattern to organize your project via the
      ``flasker.current_project`` proxy (cf. `Quickstart`_).

    - A command line tool from where you can launch the Flask buit in Werkzeug_
      server, start Celery workers and the Flower_ tool, and run a shell in the
      current project context.

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
Celery and SQLAlchemy running in moments (the code is available on GitHub in
``examples/basic/``).

The basic folder hierarchy for a Flasker project looks something like this:

.. code:: bash

  project/
    conf.cfg    # configuration
    app.py      # code

Where ``conf.cfg`` is:

.. code:: cfg

  [PROJECT]
  MODULES = app

The ``MODULES`` option contains the list of python modules which belong
to the project. Inside each of these modules we can use the
``flasker.current_project`` proxy to get access to the current project
instance (which gives access to the configured Flask application, the Celery
application and the SQLAlchemy database session registry). This is the
only option required in a Flasker project configuration file.

Here is a sample ``app.py``:

.. code:: python

   from flasker import current_project

   flask_app = current_project.flask    # Flask app
   celery_app = current_project.celery  # Celery app
   session = current_project.session    # SQLAlchemy scoped session maker

   # for this simple example we will only use flask_app

   @flask_app.route('/')
   def index():
    return 'Hello World!'

Once these two files are in place, we can already start the server! We 
simply run (from the command line in the ``project/`` directory):

.. code:: bash

   $ flasker server 
   * Running on http://0.0.0.0:5000/

We can check that our server is running for example using Requests_ (if we
navigate to the same URL in the browser, we would get similarly exciting
results):

.. code:: python

   In [1]: import requests
   In [2]: print requests.get('http://localhost:5000/').text
   Hello World!


Configuring your project
------------------------

In the previous example, the project was using the default configuration,
this can easily be changed by adding options to the ``conf.cfg`` file. 
Here is an example of a customized configuration file:

.. code:: cfg

  [PROJECT]
  MODULES = app
  [ENGINE]
  URL = sqlite:///db.sqlite   # the engine to bind the session on
  [FLASK]
  DEBUG = true                # generic Flask options
  TESTING = true

For an exhaustive list of all the options available, please refer to the
documentation on GitHub Pages.

Finally, of course, all your code doesn't have to be in a single file. You can
specify a list of modules to import in the ``MODULES`` option, which will all
be imported on project startup. For an example of a more complex application,
you can check out the code in ``examples/flisker``.


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

