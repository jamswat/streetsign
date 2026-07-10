#!.virtualenv/bin/python3
# -*- coding: utf-8 -*-
'''
    Simple run script for streetsign_server.

    Usage:

    ./run.sh
        (starts the development internal flask server.  FOR DEVELOPMENT ONLY!)

    ./run.sh waitress
        (starts the server running with the waitress production server)
'''



# Configuration Options:

from os import environ
import logging

__HOST__ = environ.get('HOST', '0.0.0.0')
__PORT__ = int(environ.get('PORT', '5000'))
__THREADS__ = 8 # (for waitress, only)

# Initialise unicode:

import sys

# Set up logging before loading the app so import-time messages are captured.
logging.basicConfig(
    level=environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)
logging.getLogger('waitress').setLevel(logging.INFO)

# Load the app:

from streetsign_server import app, assert_secret_key_is_safe

# Whether to run the dev server with the (RCE-capable) Werkzeug debugger.
# Off by default; opt in explicitly with FLASK_DEBUG=1. The debugger must
# never be exposed on a public interface.
__DEBUG__ = environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes', 'on')

# And start the correct server

if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] == 'waitress':
            assert_secret_key_is_safe()
            print("'Production' Server with Waitress.")
            print("Press <Ctrl-C> to stop")
            from waitress import serve
            serve(app, host=__HOST__, port=__PORT__, threads=__THREADS__)
        elif sys.argv[1] == 'profiler':
            print("Loading dev server with profiling on.")
            print("Press <Ctrl-C> to stop")
            from werkzeug.middleware.profiler import ProfilerMiddleware
            app.config['PROFILE'] = True
            app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[20])
            app.run(debug=__DEBUG__)
    else:
        print("Starting Development Server (DEVELOPMENT ONLY)...")
        if __DEBUG__:
            # With the interactive debugger enabled, refuse to listen on a
            # public interface - it is a remote-code-execution console.
            host = '127.0.0.1'  # pylint: disable=invalid-name
            print("Debugger ON - binding to 127.0.0.1 only.")
        else:
            host = __HOST__
        print("Press <Ctrl-C> to stop")
        app.run(host=host, port=__PORT__, debug=__DEBUG__)
