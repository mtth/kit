Flask App Template
==================

Requirements
------------

Python modules::

    pip install Flask
    pip install SQLAlchemy
    pip install Celery
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

Running the app
---------------

Start the celery worker::

    celery worker -A app -l info

Start the app server (using Werkzeug)::

    python run.py

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
