Flasker
=======

**What Flasker is**
Flask_ webapp template with optional Celery_ backend.

**What Flasker isn't**
An easy way to learn Flask, SQLAlchemy and Celery. Flasker works behind the scene to tie these three tools together so that it 'works' but at the same time exposes the bare webapp, celery worker and database objects. This integration is meant to be as transparent as possible, to let you configure these individually according to your project needs.

Feature highlights
==================

* `Database backend ready to use`_
* `User authentication using Google OAuth`_
* `Running and scheduling jobs with Celery`_
* Includes jQuery_ and Bootstrap_ CSS and JS libraries

Quickstart
==========

* **Installation**::

    $ pip install flasker

* **To create a new project**::

    $ flasker

  You will be prompted...
  This will run the server (using Werkzeug) on port 5050. Also:

  * Append the ``-d`` flag to run the server in debug mode (enables autoreload and in-browser debugger)
  * A list of available commands is available by running ``python manage.py``

Features
========

Database backend ready to use
-----------------------------

The app uses SQLAlchemy_ and offers several helpers to create persistent models. By default, the database backend uses SQLite_ but this can be changed by editing ``APP_DB_URL`` in the ``app/core/config.py`` file. If MySQL_ is used, full write concurrency is supported (even with the Celery_ worker).

Here are a few of the helpers available on the default ``Base`` model class:

* Jsonifiable
* Loggable
* Cacheable

And more:

* api_response
* Dict

User authentication using Google OAuth
--------------------------------------

* **Setup**

Inside ``app/core/config.py``, set ``USE_OAUTH = True`` and fill in the ``GOOGLE_CLIENT_ID`` and ``GOOGLE_CLIENT_SECRET``. If you don't know what these are, you can read about them and create your own in the `Google API Console`_.

* **Usage**

  To restrict some pages to logged-in users, add the `login_required` to the corresponding view. E.g::

    @app.route('/some_url')
    @login_required
    def some_protected_page():
      return render_templage('template.html')

  At first, there are no authorized users, in order to authorize someone to log in, run the following command and enter the email you want to authorize when prompted::

    $ python manage.py add_user

  You can view the list of authorized users at any time by running::

    $ python manage.py view_users

Running and scheduling jobs with Celery
---------------------------------------

* **Setup**

First, if you don't yet have Redis, here is how to install it::

    $ curl -O http://download.redis.io/redis-stable.tar.gz
    $ tar xvzf redis-stable.tar.gz
    $ cd redis-stable
    $ make
    $ make test
    $ sudo cp redis-server /usr/local/bin/
    $ sudo cp redis-cli /usr/local/bin/
  
Finally, inside ``app/core/config.py``, set ``USE_CELERY = True``.

* **Usage**
  
  Run the following command to start the worker::

    $ python manage.py run_worker

  To learn how to create tasks and schedule them, please refer to the official Celery_ documentation.

* **Optional extra steps**

  * Daemonizing redis on a mac

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

Running the server on Apache
----------------------------

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
=======

* http://redis.io/topics/quickstart
* http://naleid.com/blog/2011/03/05/running-redis-as-a-user-daemon-on-osx-with-launchd/
* http://infinitemonkeycorps.net/docs/pph/
* https://google-developers.appspot.com/chart/interactive/docs/index
* http://codemirror.net/
* http://networkx.lanl.gov/index.html

.. _Bootstrap: http://twitter.github.com/bootstrap/index.html
.. _Flask: http://flask.pocoo.org/docs/api/
.. _Jinja: http://jinja.pocoo.org/docs/
.. _Celery: http://docs.celeryproject.org/en/latest/index.html
.. _Datatables: http://datatables.net/examples/
.. _SQLAlchemy: http://docs.sqlalchemy.org/en/rel_0_7/orm/tutorial.html
.. _MySQL: http://dev.mysql.com/doc/
.. _`Google OAuth 2.0`: https://developers.google.com/accounts/docs/OAuth2
.. _`Google API console`: https://code.google.com/apis/console
.. _jQuery: http://jquery.com/
.. _`jQuery UI`: http://jqueryui.com/
