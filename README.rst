Flask App Template
==================

About
-----

Template to get a Flask_ webapp running out of the box. The package comes with a functional Celery_ backend.

Feature highlights
------------------

*   Database setup built in. You only need to give SQLAlchemy_ the database URI and all sessions and connections (from the app and worker) are handled. If MySQL_ is used as storage backend, write concurrency is supported. A few helper classes and methods are also provided: dictionary column, property caching, custom queries, pagination.
*   Job tracking for Celery tasks.
*   User authentication using Google Auth (requires registering the app on the `Google API console`_).
*   Datatables_ plugin for easy integration of interactive tables. jQuery_ and `jQuery UI`_ are also included.
*   Sleek Bootstrap_ and Jinja_ (from Flask) templating.

Coming soon:

*   Automatic scheduled cache refresh using Celery

Installation
------------

Python modules::

    pip install Flask
    pip install SQLAlchemy
    pip install Celery
    pip install Flask-Script
    pip install flask-login
    pip install redis

Redis::

    curl -O http://download.redis.io/redis-stable.tar.gz
    tar xvzf redis-stable.tar.gz
    cd redis-stable
    make
    make test
    sudo cp redis-server /usr/local/bin/
    sudo cp redis-cli /usr/local/bin/

Enter your Google OAuth credentials in ``app/config/flask.py``.

Running the app
---------------

Start the celery worker::

    python manage.py run_worker

Start the app server (using Werkzeug)::

    python manage.py run_server

Optional steps
--------------

*   Daemonizing redis on a mac

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

*   Daemonizing the celery worker

    TODO

Sources
-------

*   http://redis.io/topics/quickstart
*   http://naleid.com/blog/2011/03/05/running-redis-as-a-user-daemon-on-osx-with-launchd/

*   http://infinitemonkeycorps.net/docs/pph/
*   https://google-developers.appspot.com/chart/interactive/docs/index
*   http://codemirror.net/
*   http://networkx.lanl.gov/index.html

.. _Bootstrap: http://twitter.github.com/bootstrap/index.html
.. _Flask: http://flask.pocoo.org/docs/api/
.. _Jinja: http://jinja.pocoo.org/docs/
.. _Celery: http://docs.celeryproject.org/en/latest/index.html
.. _Datatables: http://datatables.net/examples/
.. _SQLAlchemy: http://docs.sqlalchemy.org/en/rel_0_7/orm/tutorial.html
.. _MySQL: http://dev.mysql.com/doc/
.. _`Google API console`: https://code.google.com/apis/console
.. _jQuery: http://jquery.com/
.. _jQuery-ui: http://jqueryui.com/
