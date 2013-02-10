Flasker
=======

A lightweight Flask_ webapp project manager with built in ORM'ed database using SQLAlchemy_ and Celery_ backend support.

- What Flasker is!
  
    - A transparent integration of Flask, SQLAlchemy and Celery which lets you
      configure these individually according to your project needs via a single
      ``.cfg`` file.
    
    - A simple pattern to organize your project via the ``current_project``
      proxy (cf. `Structuring your project`_ for an example). No more
      complicated import schemes!

    - A command line tool from where you can create new projects, launch the
      Flask buit in Werkzeug server, start Celery workers and the Flower_ tool,
      and run a shell in the current project context (inspired by Flask-Script_).

- What Flasker isn't?

    - A simplified version of Flask, Celery, and SQLAlchemy. Flasker handles the
      setup but intentionally leaves you free to interact with the raw Flask,
      Celery and SQLAlchemy session objects. Some knowledge of these frameworks is
      therefore required. 

Flasker also comes with two optional extensions:

- `Authentication`_

- `ReSTful API`_ *under development*


Quickstart
----------

- Installation:

  .. code:: bash

    $ pip install flasker

- To create a new project:

  .. code:: bash

    $ flasker new basic

  This will create a project configuration file ``default.cfg`` in the
  current directory and a basic Bootstrap_ themed app (this can be turned off
  with the ``-a`` flag).

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
section). Inside each of these you can use the ``current_project`` proxy to get
access to the Flask application object, the Celery application object and the
SQLAlchemy database sessions. Therefore a very simple pattern inside each module
is to do:

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
  # but you get the idea :). and now you can do stuff with each...

  @app.route('/')
  def index():
    """A random view."""
    return render_template('index.html')

  @celery.task
  def task():
    """And a great task."""
    pass

  # and so on...

Once Flasker has finished importing all your project module files and configuring the applications, it handles startup.

To use


Extensions
----------

Authentication
**************

This extension uses Flask-Login_ to handle sessions and `Google OAuth 2`_ to handle
authentication.

Adding the following code to any one of your modules will allow you to restrict
access to your application:

.. code:: python

  from flasker import current_project
  from flasker.ext.auth import GoogleAuthManager

  auth_manager = GoogleAuthManager(
    client_id='your_google_client_id',
    authorized_emails=['hers@email.com', 'his@email.com', ...],
    callback_url='/oauth2callback'
  )
  current_project.register_manager(auth_manager)

By default the authentication manager will protect all your views. You can
disable this behavior by passing the constructor option
``protect_all_views=False`` and individually protect views with the
``flask.ext.login.login_required`` decorator.


ReSTful API
***********

This extension is meant to very simply expose URL endpoints for your models.

There exist other great ReSTful extensions for Flask. Here are the 
main differences with two popular ones:

* FlaskRESTful_ works at a sligthly lower level. It provides great tools but it
  would still require work to tie them with each model. Here, the extension uses
  the Flasker model structure to do most of the work.

* Flask-Restless_ is similar in that it also intends to bridge the gap between
  views and SQLAlchemy models. However the Flasker API is built to provide:

  * *Faster queries*: the 'jsonification' of model entities is heavily optimized
    for large queries.
  * *More flexibility*: API responses are not restricted to returning model columns but
    also return properties.
  * *Convenient access to nested models*: queries can go arbitrarily deep
    within nested models (the extension takes care of not repeating information).
    This is especially useful with a client-side library such as Backbone-Relational_.
  * *More endpoints*: each one-to-many relation can have its own model specific endpoint.
  * *Support for models with composite primary keys*

  Nevertheless this extension is much younger and currently lacks several great
  features offered by Flask-Restless (such as arbitrary queries and function
  evaluation).

Here is a very simple sample file:

.. code:: python

  from flasker import current_project
  from flasker.ext.api import APIManager, Model
  from sqlalchemy import Column, ForeignKey, Integer, String

  # Create the APIManager

  api_manager = APIManager(add_all_models=True)
  current_project.register_manager(api_manager)

  # Define the models

  class House(Model):

    id = Column(Integer, primary_key=True)
    address = Column(String(128))

  class Cat(Model):

    name = Column(String(64), primary_key=True)
    house_id = Column(ForeignKey('houses.id'))
    house = relationship('House', backref='cats')

Which will create the following endpoints:

* ``/api/houses/ (GET, POST)``
* ``/api/houses/<id> (GET, PUT, DELETE)``
* ``/api/houses/<id>/cats/ (GET, PUT)``
* ``/api/houses/<id>/cats/<position> (GET)``
* ``/api/cats/ (GET, POST)``
* ``/api/cats/<name> (GET, PUT, DELETE)``


Utilities
---------

Available utilities include:

* Caching
* Jsonifying
* Logging


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
