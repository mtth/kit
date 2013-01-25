Flasker
=======

A Flask_ webapp project manager with built in ORM'ed database using SQLAlchemy_ and Celery_ backend support.

- What Flasker is!
  
    - A transparent integration of Flask, SQLAlchemy and Celery which lets you
      configure these individually according to your project needs via a single
      ``.cfg`` file (cf. `Sample config file`_).
    
    - A very simple pattern to organize your project via the
      ``current_project`` proxy. No more complicated import schemes!

    - OAuth (via `Google OAuth 2`_) and a bunch of utilities via the ``util``
      module (for convenient logging, efficient API responses, property caching,
      and more).

    - A command line tool from where you can create new projects, launch the
      Flask buit in Werkzeug server, start Celery workers and the Flower_ tool,
      and run a shell in the current project context (inspired by Flask-Script_).

- What Flasker isn't?

    - A simplified version of Flask, SQLAlchemy and Celery. Flasker handles the
      setup but purposefully leaves you free to interact with the raw Flask,
      Celery and database objects. Some knowledge of these frameworks is
      therefore required. 

Quickstart
----------

- Installation::

    $ pip install flasker

- To create a new project::

    $ flasker new -a dev

  This will create a default project configuration file ``project.cfg`` in the
  current directory (the ``-a`` flag triggers the creation of a basic boostrap
  app).

- Editing your project:

  The ``flasker`` module exposes a ``current_project`` proxy which grants you
  access to the Flask app, the Celery application and the SQLAlchemy database
  object respectively through its attributes ``app``, ``celery``, ``db``.
  Inside each project module (defined in the ``MODULES`` option of the
  configuration file) you can then do, for example::

    from flasker import current_project

    app = current_project.app

    # do stuff with the app


- Next steps::

    $ flasker -h

  This will list all available commands for that project:

  - Running the app server
  - Starting a worker for the Celery backend
  - Running the flower worker management app
  - Starting a shell in the current project context (useful for debugging)

  Extra help is available for each command by typing::

    $ flasker <insert_command> -h


Sample config file
------------------

Here is a minimalistic project configuration file::

  [DEFAULT]
  NAME: My Project
  SHORTNAME: my_project
  CONFIG_TYPE: dev
  [PROJECT]
  MODULES: app.views,app.tasks
  DB_URL: sqlite:///db/db.sqlite
  [APP]
  DEBUG: True
  TESTING: True
  [CELERY]
  BROKER_URL: redis://localhost:6379/0
  CELERYD_CONCURRENCY: 2
   

Using OAuth
-----------

To restrict access to your webapp to some users, you will need to enter your
Google Client ID (from the `Google API console`_) in the ``OAUTH_CLIENT``
configuration option and also enter authorized emails in the
``AUTHORIZED_EMAILS`` option. Then, use the ``login_required`` decorator from
Flask-Login_ to protect your views (cf. the docs for examples and a tutorial).


Utilities
---------

TODO


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
