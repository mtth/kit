Flasker
=======

Under development. Visit https://github.com/mtth/flasker for the latest version.

A Flask_ webapp project manager with built in ORM'ed database using SQLAlchemy_ and Celery_ backend support.

- What Flasker is!
  
    - A transparent integration of Flask, SQLAlchemy and Celery which lets you
      configure these individually according to your project needs via a single
      ``.cfg`` file (cf. `Config file API`_).
    
    - A simple pattern to organize your project via the ``current_project`` proxy.
      No more complicated import schemes!

    - A command line tool from where you can create new projects, launch the
      Flask buit in Werkzeug server, start Celery workers and the Flower_ tool,
      and run a shell in the current project context (inspired by Flask-Script_).

- What Flasker isn't?

    - A simplified version of Flask, SQLAlchemy and Celery. Flasker handles the
      setup but intentionally leaves you free to interact with the raw Flask,
      Celery and database objects. Some knowledge of these frameworks is
      therefore required. 

Flasker also comes with two optional extensions:

- `ReSTful API extension`_

- `Authentication extension`_


Quickstart
----------

- Installation::

    $ pip install flasker

- To create a new project::

    $ flasker new basic

  This will create a project configuration file ``default.cfg`` in the
  current directory (cf `Config file API`_ for more info on the available
  configurations through the ``new`` command) and a basic Bootstrap_ themed
  app in an ``app`` folder (this can be turned off with the ``-a`` flag).

  Already, you should be able to run your app by running ``flasker server``.

- Editing your project:

  The ``flasker`` module exposes a ``current_project`` proxy which grants 
  access to the Flask app, the Celery application and the SQLAlchemy database
  object respectively through its attributes ``app``, ``celery``, and ``db``.
  Inside each project module (as defined by the ``MODULES`` option of the
  configuration file) you can then do, for example::

    from flasker import current_project

    app = current_project.app
    # do stuff

- Next steps::

    $ flasker -h

  This will list all available commands for that project:

  - Running the app server
  - Starting a worker for the Celery backend
  - Running the flower worker management app
  - Starting a shell in the current project context (useful for debugging)

  Extra help is available for each command by typing::

    $ flasker <insert_command> -h


Config file API
---------------

Here is what a minimalistic project configuration file looks like::

  [PROJECT]
  NAME: My Project
  MODULES: app.views, app.tasks
  DB_URL: sqlite:///db/db.sqlite
  [APP]
  DEBUG: True
  TESTING: True
  [CELERY]
  BROKER_URL: redis://
  CELERYD_CONCURRENCY: 2
   
The following keys are valid in the ``PROJECT`` section:

* ``NAME``, name of the project
* ``MODULES``, modules to import on project load (comma separated list)
* ``DB_URL``, URL of database (defaults to the in memory ``sqlite://``)
* ``APP_FOLDER``, path to Flask application root folder, relative to the
  configuration file (defaults to ``app/``)
* ``APP_STATIC_FOLDER``, path to folder where the Flask static files lie,
  relative to the Flask root folder (defaults to ``static/``)
* ``APP_TEMPLATE_FOLDER``, path to folder where the Flask template files lie,
  relative to the Flask root folder (defaults to ``templates/``)
* ``STATIC_URL``, optional URL to serve static files

The ``APP`` section can contain any Flask_ configuration options (as defined here: 
http://flask.pocoo.org/docs/config/) and the ``CELERY`` section can contain any
Celery_ configuration options (as defined here: http://docs.celeryproject.org/en/latest/configuration.html). Any options defined in either section will be passed along
to the corresponding object.

There are two pregenerated configurations available through the ``flasker new`` command:

* ``basic``, minimal configuration
* ``celery``, includes default celery configuration with automatic
  worker hostname generation and task routing


Extensions
----------

ReSTful API extension
*********************

This extension is meant to very simply expose URL endpoints for your models.

There exist other great ReSTful extensions for Flask_. Here are the 
main differences with two popular ones:

* FlaskRESTful_

  FlaskRESTful works at a sligthly lower level. It provides great tools but it
  would still require work to tie them with each model. Here, the extension uses
  the Flasker model structure to do most of the work.

* Flask-Restless_

  Flask-Restless is closer to the purpose of this extension at first glance.
  In comparison, the API manager is intended to provide:

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

Here is a very simple sample file::

  from flasker import current_project
  from flasker.ext.api import APIManager
  from flasker.util import Model
  from sqlalchemy import Column, ForeignKey, Integer, Unicode

  # Create the APIManager

  api_manager = APIManager(add_all_models=True)
  current_project.register_manager(api_manager)

  # Define the models

  class House(Model):

    id = Column(Integer, primary_key=True)
    address = Column(Unicode(128))

  class Cat(Model):

    name = Column(Unicode(64), primary_key=True)
    house_id = Column(ForeignKey('houses.id'))
    house = relationship('House', backref='cats')

Which will create the following endpoints:

* ``/api/houses/ (GET, POST)``
* ``/api/houses/<id> (GET, PUT, DELETE)``
* ``/api/houses/<id>/cats/ (GET, PUT)``
* ``/api/houses/<id>/cats/<position> (GET)``
* ``/api/cats/ (GET, POST)``
* ``/api/cats/<name> (GET, PUT, DELETE)``

Cf. the Wiki_ for the complete list of available options.


Authentication extension
************************

This extension uses Flask-Login_ to handle sessions and `Google OAuth 2`_ to handle
authentication.

Adding the following code to any one of your modules will allow you to restrict
access to your application::

  from flasker import current_project
  from flasker.ext.auth import GoogleAuthManager

  auth_manager = GoogleAuthManager(
    client_id='your_google_client_id',
    authorized_emails=['hers@email.com', 'his@email.com', ...]
  )
  current_project.register_manager(auth_manager)

Cf. the Wiki_ for the complete list of available options.


Utilities
---------

Available utilities include:

* Caching
* Jsonifying
* Logging

Cf. the Wiki_.


Other stuff
-----------

- Setting up Redis::

    $ curl -O http://download.redis.io/redis-stable.tar.gz
    $ tar xvzf redis-stable.tar.gz
    $ cd redis-stable
    $ make
    $ make test
    $ sudo cp redis-server /usr/local/bin/
    $ sudo cp redis-cli /usr/local/bin/

  To daemonize redis on a mac:

    Create a plist file::

      $ sudo vim /Library/LaunchDaemons/io.redis.redis-server.plist

    Copy the following contents::
    
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>io.redis.redis-server</string>
        <key>ProgramArguments</key>
        <array>
          <string>/usr/local/bin/redis-server</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
      </dict>
      </plist>

- Running the server on Apache:

  Create a file called `run.wsgi` in the main directory with the following contents::

    # Virtualenv activation
    from os.path import abspath, dirname, join
    activate_this = abspath(join(dirname(__file__), 'venv/bin/activate_this.py'))
    execfile(activate_this, dict(__file__=activate_this))

    # Since the application isn't on the path
    import sys
    sys.path.insert(0, abspath(join(dirname(__file__)))

    # App factory
    from app import make_app
    application = make_app()

  Then add a virtualhost in your Apache virtual host configuration file (often found at `/etc/apache2/extra/httpd-vhosts.conf`) with the following configuration::

    <VirtualHost *:80>
      ServerName [server_name]
      WSGIDaemonProcess [process_name] user=[process_user] threads=5
      WSGIScriptAlias / [path_to_wsgi_file]
      <Directory [path_to_root_directory]>
          WSGIProcessGroup [process_name]
          WSGIApplicationGroup %{GLOBAL}
          Order deny,allow
          Allow from all
      </Directory>
      ErrorLog "[path_to_error_log]"
      CustomLog "[path_to_access_log]" combined
    </VirtualHost>
  
Sources
-------

- http://redis.io/topics/quickstart
- http://naleid.com/blog/2011/03/05/running-redis-as-a-user-daemon-on-osx-with-launchd/
- http://infinitemonkeycorps.net/docs/pph/
- https://google-developers.appspot.com/chart/interactive/docs/index
- http://codemirror.net/
- http://networkx.lanl.gov/index.html

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
