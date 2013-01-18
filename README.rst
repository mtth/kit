Flask App Template
==================

Flask_ webapp template with optional Celery_ backend.

Feature highlights
------------------

* Database interactions using SQLAlchemy_
* User authentication using `Google OAuth 2.0`_
* Includes jQuery_ and Bootstrap_ CSS and JS libraries
* Celery_ for scheduling and running long jobs

Quickstart
----------

* **Installation** Clone this repo on your machine::

    git clone git://github.com/mtth/flask.git
    cd flask
    sudo easy_install virtualenv  # optional (if you don't have virtualenv)
    virtualenv venv
    . venv/bin/activate
    pip install Flask-Script
    pip install SQLAlchemy

* **Running the app** Start the app server (using Werkzeug)::

    python manage.py run_server

  NB:

  * Append the ``-d`` flag to run the server in debug mode
  * A list of available commands by the manager is available by running ``python manage.py``

Optional steps
--------------

* Using Google OAuth

  * **Setup** Python module requirements::

      pip install flask-login

    Inside ``app/core/config.py``, set ``USE_OAUTH = True`` and fill in the ``GOOGLE_CLIENT_ID`` and ``GOOGLE_CLIENT_SECRET``. If you don't know what these are, you can read about them and create your own in the `Google API Console`_.

  * **Usage** To restrict some pages to logged-in users, add the `login_required` to the corresponding view. E.g::

      @app.route('/some_url')
      @login_required
      def some_protected_page():
        return render_templage('template.html')

    At first, there are no authorized users, in order to authorize someone to log in, run the following command::

      python manage.py add_user

    You can view the list of authorized users at any time by running::

      python manage.py view_users

* Using Celery

  * **Setup** Python module requirements::

      pip install Celery
      pip install redis

    If you don't yet have Redis, here is how to install it::

      curl -O http://download.redis.io/redis-stable.tar.gz
      tar xvzf redis-stable.tar.gz
      cd redis-stable
      make
      make test
      sudo cp redis-server /usr/local/bin/
      sudo cp redis-cli /usr/local/bin/

  * **Usage** Run the following command to start the worker::

      python manage.py run_worker

    To learn how to create tasks and schedule them, please refer to the official Celery_ documentation.

  * **Optional extra steps**

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

* Running the server on Apache

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
