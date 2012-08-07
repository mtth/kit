#!/usr/bin/env python

"""Run the app server."""

from getopt import getopt, GetoptError

from subprocess import call

from sys import argv, exit

from app import make_app

def main(command, options):
    """Command line options parser."""
    if command == 'server':
        start_web_server(options)
    elif command == 'celery': 
        start_celery_worker(options)
    else:
        print 'Usage: run.py [-d -h <host> -p <port>]'
        exit(2)

def start_web_server(options):
    debug = False
    host = '0.0.0.0'
    port = 5000
    try:
        opts, args = getopt(
                options,
                'vdh:p:',
                ['debug', 'host', 'port']
        )
    except GetoptError:
        print 'Usage: run.py [-d -h <host> -p <port>]'
        exit(2)
    for opt, arg in opts:
        if opt == '-v':
            print 'Usage: run.py [-d -h <host> -p <port>]'
            exit()
        elif opt in ('-d', '--debug'):
            debug = True
        elif opt in ('-h', '--host'):
            host = arg
        elif opt in ('-p', '--port'):
            port = int(arg)
    app = make_app(debug=debug)
    app.run(
            host=host,
            port=port,
            debug=debug
    )

def start_celery_worker(options):
    try:
        opts, args = getopt(
                options,
                'vdh:p:',
                ['debug', 'host', 'port']
        )
    except getopt.GetoptError:
        print 'Usage: run.py [-d -h <host> -p <port>]'
        exit(2)
    call(['celery', 'worker', '-A', 'app/core/celery.py'])

if __name__ == '__main__':
    if len(argv) < 2:
        print 'Usage'
        exit()
    else:
        main(argv[1], argv[2:])
