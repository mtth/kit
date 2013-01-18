Flask App Template
==================

Flask_ webapp template with optional Celery_ backend.

Feature highlights
------------------

* Database interactions using SQLAlchemy_
* User authentication using `Google Auth 2.0`_
* Includes jQuery_ and Bootstrap_ CSS and JS libraries
* Celery_ for scheduling and running long jobs

Quickstart
----------

* Installation

  Clone this repo on your machine::

    git clone git://github.com/mtth/flask.git
    cd flask

  Setting up the `virtual environment` (optional but recommended)::

    virtualenv venv
    . venv/bin/activate

  Installing dependencies::

    pip install Flask-Script
    pip install SQLAlchemy

* Running the app

  Start the app server (using Werkzeug)::

    python manage.py run_server

  NB:

    * Append the ``-d`` flag to run the server in debug mode
    * A list of available commands by the manager is available by running ``python manage.py``

Optional steps
--------------

Using Celery
************

  * Requirements:

    Python module requirement::

      pip install redis

    If you are planning on using the Celery backend, and don't yet have Redis, here is how to install it::

      curl -O http://download.redis.io/redis-stable.tar.gz
      tar xvzf redis-stable.tar.gz
      cd redis-stable
      make
      make test
      sudo cp redis-server /usr/local/bin/
      sudo cp redis-cli /usr/local/bin/

  * Start the celery worker

    Run the following command::

      python manage.py run_worker

  * Extra steps:

    * Daemonizing redis on a mac

      Create a plist file::

        sudo vim /Library/LaunchDaemons/io.redis.redis-server.plist

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
**

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


Using Google OAuth
**

  TODO
  
Sources
-------

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
