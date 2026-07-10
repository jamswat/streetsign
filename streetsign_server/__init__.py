# -*- coding: utf-8 -*-
"""  StreetSign Digital Signage Project
     (C) Copyright 2013 Daniel Fairhead

    StreetSign is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    StreetSign is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with StreetSign.  If not, see <http://www.gnu.org/licenses/>.

"""

from os.path import dirname, join as pathjoin
import logging

from flask import Flask, json
from whitenoise import WhiteNoise

logger = logging.getLogger(__name__)

try:
    import config
except ImportError:
    logger.warning("Config file missing, using defaults.")
    import config_default as config

app = Flask(__name__) # pylint: disable=invalid-name
app.config.from_object(config)

# Jinja filter for parsing JSON strings in templates.
app.jinja_env.filters['from_json'] = json.loads

# Configure the Flask application logger from LOG_LEVEL.
import logging as _logging
app.logger.setLevel(getattr(_logging, app.config.get('LOG_LEVEL', 'INFO'),
                            _logging.INFO))

# The known, insecure default SECRET_KEY signs session cookies, so a public
# default lets anyone forge sessions. Warn loudly on import; the server
# entrypoints (run.py) call assert_secret_key_is_safe() to hard-fail before
# actually serving requests in production.
_INSECURE_KEY = app.config.get('DEFAULT_INSECURE_SECRET_KEY',
                               'dev-default-key-change-in-production')

def using_insecure_secret_key():
    ''' True if SECRET_KEY is still the public, insecure default. '''
    return app.config.get('SECRET_KEY') == _INSECURE_KEY

def assert_secret_key_is_safe():
    ''' Refuse to serve in production with the insecure default SECRET_KEY.
        Call this from the server entrypoint before binding a socket. '''
    if using_insecure_secret_key():
        raise RuntimeError(
            'SECRET_KEY is set to the insecure default. Set the SECRET_KEY '
            'environment variable (or config.py) to a unique random value '
            'before running. Generate one with: '
            'python3 -c "import uuid; print(uuid.uuid4())"')

if using_insecure_secret_key():
    logger.warning('using the insecure default SECRET_KEY. '
                  'Set SECRET_KEY before deploying!')

def _static_security_headers(headers, _path, _url):
    ''' Add security headers to WhiteNoise-served static file responses,
        matching those applied to dynamic responses by set_security_headers. '''
    headers['X-Content-Type-Options'] = 'nosniff'
    headers['X-Frame-Options'] = 'SAMEORIGIN'

# Serve static assets in-process via WhiteNoise instead of an nginx sidecar.
# Built-in assets (main.js, style.css, etc.) are baked into the image.
# User uploads live under /static/user_files/ on a persistent volume and are
# served through the same WhiteNoise pipeline. autorefresh=True is load-bearing
# here — without it, newly uploaded files would 404 until a restart because
# WhiteNoise only scans the filesystem at startup. For a signage server with
# a handful of always-on displays the extra stat() per static request is
# negligible. Requests that don't match a static file fall through to Flask.
app.wsgi_app = WhiteNoise(
    app.wsgi_app,
    root=pathjoin(dirname(__file__), 'static'),
    prefix='static',
    autorefresh=True,
    add_headers_function=_static_security_headers,
)

@app.after_request
def set_security_headers(response):
    ''' Apply security headers to Flask-handled (dynamic) responses. WhiteNoise
        static responses get the same headers via _static_security_headers. '''
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    return response

from . import models
import streetsign_server.views as views
from .models import \
     User, Group, Post, Feed, FeedPermission

__version__ = '1.1.0'

@app.context_processor
def inject_version():
    return {'app_version': __version__}

models.init()
