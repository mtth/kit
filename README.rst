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

- A ReSTful API_ extension

- An Authentication_ extension using Flask-Login_ and `Google OAuth 2`_.


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

API
***

**Preface** There exists a Flask_ API extension (Flask-Restless_) that shares a similar
purpose at first glance. However this extension was built with the goal to provide:

  * *Faster queries*: the 'jsonification' of model entities is heavily optimized
    for large queries.
  * *More flexibility*: API responses are not restricted to returning model columns but
    also return properties.
  * *Convenient access to nested models*: queries can go arbitrarily deep
    within nested models (the extension takes care of not repeating information).
    This is especially useful with a client-side library such as Backbone-Relational_.
  * *More endpoints*: each one-to-many relation has its own model specific endpoint.
  * *Support for models with composite primary keys*

Nevertheless this extension is much younger and currently lacks several great
features offered by Flask-Restless_ (such as arbitrary queries and function
evaluation).

How to use::

  from flasker import current_project
  from flasker.ext.api import APIManager

  api_manager = APIManager()
  api_manager.add_all_models(methods=['GET'])
  current_project.register_manager(api_manager)

This will add URL endpoints for all registered models and allow GET requests for each.
Models are defined as subclasses of the ``flasker.util.Model`` class. They can have
arbitrary keys and columns. For POST and PUT requests to work, the constructor must
accept kwargs arguments (similar to the default implementation).  You can also of
course add models individually::

  api_manager.add_model(YourModel, methods=['GET', 'POST'])

Options specified anew for a given model will override previous ones. ``add_model``
and ``add_all_models`` accept the same arguments:

* ``Model``, the model class
* ``relationships``, whether or not to create endpoints for one-to-many
  relationships on the model. Can be a list of keys, ``True`` (default) to
  create all or ``False`` to create none.
* ``allow_put_many``, allow PUT method for collections (defaults to ``True``).
* ``methods``, list of allowed methods (defaults to ``['GET', 'POST', 'PUT',
  'DELETE']``).

URLs are generated from the model's tablename and relationship keys. For example,
assume we have defined the following models::

  from flasker.util import Model
  from sqlalchemy import Column, ForeignKey, Integer, Unicode

  class House(Model):

    id = Column(Integer, primary_key=True)
    address = Column(Unicode(128))

  class Cat(Model):

    name = Column(Unicode(64), primary_key=True)
    house_id = Column(ForeignKey('houses.id'))

    house = relationship('House', backref='cats')

Calling ``api_manager.add(House)`` will create the following endpoints:

* ``/api/houses/``
* ``/api/houses/<id>``
* ``/api/houses/<id>/cats/``
* ``/api/houses/<id>/cats/<position>``

For convenience, the root url ``api/`` yields a list of all endpoints, columns
and relationships available through the API.  Note that relationship endpoints
for now only allow GET and PUT requests.

Authentication
**************

Adding the following code to any one of your modules will allow you to restrict access
to your application::

  from flasker import current_project
  from flasker.ext.auth import GoogleAuthManager

  auth_manager = GoogleAuthManager(
    CLIENT_ID='your_google_client_id',
    AUTHORIZED_EMAILS=['hers@email.com', 'his@email.com', ...]
  )

  current_project.register_manager(auth_manager)

Here is the full list of options available to the ``GoogleAuthManager``:

* ``CLIENT_ID``, your Google client ID (which can be found in the `Google API console`_)
* ``AUTHORIZED_EMAILS``, a list or comma separated string of emails that can login
  (defaults to the empty string)
* ``PROTECT_ALL_VIEWS``, if ``True`` (default), all the views (not including
  statically served files) will have their access restricted to logged in users.
  If set to ``False``, you should use the ``login_required`` decorator from
  Flask-Login_ to individually protect views
* ``URL_PREFIX``, the blueprint url prefix (defaults to ``/auth``)
* ``CALBACK_URL``, the callback URL for Google OAuth (defaults to ``/oauth2callback``). 
  Note that this ``CALLBACK_URL`` is concatenated with the ``URL_PREFIX`` so
  that the full callback URL you should allow in the `Google API console`_ would by
  default be ``/auth/oauth2callback``.

If you would like to include the parameters in the global configuration file
(instead of passing them directly to the constructor as we did here), you can
do that too by passing the corresponding section to the ``register_manager``
method (options specified here will override the ones from the previous
method)::

  from flasker import current_project
  from flasker.ext.auth import GoogleAuthManager

  current_project.register_manager(GoogleAuthManager(), config_section='AUTH')

Where your config file looks something like this::

  [PROJECT]
  ...
  [APP]
  ...
  [AUTH]
  CLIENT_ID = your_google_client_id
  AUTHORIZED_EMAILS = hers@email.com, his@email.com


Utilities
---------

* Caching

  * ``cached_property``
  * ``Cacheable``

* Jsonifying

  * ``jsonify``
  * ``Jsonifiable``

* Logging

  * ``Loggable``

* Misc

  * ``Dict``, dictionary with depth, width methods and ``flatten`` and
    ``unflatten`` classmethods. Also comes with the ``table`` method to transform
    nested dictionaries easily into HTML table headers.
  * ``SmartDictReader``, like ``DictReader`` from ``csv`` but automatically converts
    fields from strings to other types (either by smart guessing or by passing the
    mapping as constructor argument)


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

