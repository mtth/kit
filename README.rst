Flasker
=======

A configurable, lightweight framework that integrates Flask_, SQLAlchemy_ and Celery_.

- What Flasker is!
  
    - A one stop ``.cfg`` configuration file for Flask, Celery and the SQLAlchemy
      engine.
    
    - A simple pattern to organize your project via the
      ``flasker.current_project`` proxy (cf. `Structuring your project`_).

    - A command line tool from where you can create new projects, launch the
      Flask buit in Werkzeug server, start Celery workers and the Flower_ tool,
      and run a shell in the current project context.

- What Flasker isn't?

    - A simplified version of Flask, Celery, and SQLAlchemy. Some knowledge of these
      frameworks is therefore required. 

Flasker also comes with two extensions for commonly needed functionalities:

- Authentication
- ReSTful API *(still alpha)*

Flasker is under development. You can find the latest version in the `Flasker Git repository`_.


Quickstart
----------

- Installation:

  .. code:: bash

    $ pip install flasker

- To create a new project:

  .. code:: bash

    $ flasker new basic

  This will create a basic project configuration file ``default.cfg`` in the
  current directory and a basic Bootstrap_ themed app (this can be turned off
  with the ``-a`` flag). Another sample configuration file is available
  via ``flasker new celery`` that includes sane defaults for task routing.

- Next steps:

  .. code:: bash

    $ flasker -h

  This will list all commands now available for that project:

  - ``server`` to run the app server
  - ``worker`` to start a worker for the Celery backend
  - ``flower`` to run the flower worker management app
  - ``shell`` to start a shell in the current project context (useful for
    debugging)
  - ``new`` to create a new default configuration file

  Extra help is available for each command by typing:

  .. code:: bash

    $ flasker <command> -h


Structuring your project
------------------------

Here is a sample minimalistic project configuration file:

.. code:: cfg

  [PROJECT]
  NAME = My Project
  MODULES = app.views, app.tasks
  [ENGINE]
  # SQLAlchemy engine configuration
  URL = sqlite:///db/db.sqlite
  [APP]
  # any valid Flask configuration option can go here
  DEBUG = True
  TESTING = True
  [CELERY]
  # any valid Celery configuration option can go here
  BROKER_URL = redis://

When it starts, the ``flasker`` command line tool imports all the modules
declared in the ``MODULES`` key of the configuration file (in the ``PROJECT``
section). Inside each of these you can use the ``flasker.current_project``
proxy to get access to the Flask application object, the Celery application
object and the SQLAlchemy database sessions. Therefore a very simple pattern
inside each module is to do:

.. code:: python

  from flask import render_template
  from flasker import current_project

  # the Flask application
  app = current_project.app

  # the Celery application
  celery = current_project.celery

  # the SQLAlchemy scoped session maker 
  session = current_project.session

  # normally you probably wouldn't need all three in a single file
  # but you get the idea - and now you can do stuff with each...

  @app.route('/')
  def index():
    """A random view."""
    return render_template('index.html')

  @celery.task
  def task():
    """And a great task."""
    pass

  # and so on...

Once Flasker has finished importing all your project module files and
configuring the applications, it handles startup!

This is the simplest way you can use Flasker and there are several other
configuration options detailed in the `full documentation`_.


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
.. _full documentation: http://mtth.github.com/flasker
.. _Flasker Git repository: http://github.com/mtth/flasker
