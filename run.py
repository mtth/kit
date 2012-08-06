#!/usr/bin/env python

"""Run the app server."""

from getopt import getopt, GetoptError

from sys import argv, exit

from app import make_app

def main(argv):
    """Command line options parser."""
    debug = False
    host = '0.0.0.0'
    port = 5000
    try:
        opts, args = getopt(
                argv,
                'vdh:p:',
                ['debug', 'host', 'port']
        )
    except getopt.GetoptError:
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

if __name__ == '__main__':
    main(argv[1:])
