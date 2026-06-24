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

from flask import Flask
from whitenoise import WhiteNoise

try:
    import config
except ImportError:
    print("Config file missing, using defaults.")
    import config_default as config

app = Flask(__name__) # pylint: disable=invalid-name
app.config.from_object(config)

# Serve built-in static assets efficiently in-process (with proper cache and
# conditional-request handling) instead of via an nginx sidecar. User uploads
# live under the same /static/ tree but are persisted on a volume at runtime;
# autorefresh keeps newly uploaded files visible without a restart. Requests
# that don't match a static file fall through to Flask's normal routing.
def _static_security_headers(headers, _path, _url):
    ''' Add security headers to WhiteNoise-served static file responses,
        matching those applied to dynamic responses by set_security_headers. '''
    headers['X-Content-Type-Options'] = 'nosniff'
    headers['X-Frame-Options'] = 'SAMEORIGIN'

# Serve built-in static assets efficiently in-process (with proper cache and
# conditional-request handling) instead of via an nginx sidecar. User uploads
# live under the same /static/ tree but are persisted on a volume at runtime;
# autorefresh keeps newly uploaded files visible without a restart. Requests
# that don't match a static file fall through to Flask's normal routing.
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
from .models import DB, ALL_MODELS, \
     User, Group, Post, Feed, FeedPermission

DB.init(app.config.get('DATABASE_FILE'))
DB.bind(ALL_MODELS)