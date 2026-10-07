'''
    config_default.py:

    This file contains the configuration DEFAULTS for a streetsign installation.
    These values should NOT be changed, except as part of streetsign development.

    You should put values you want to use instead of these in config.py, which
    will include all of these values first, and then over-ride them as needed.

    Instead of changing anything here, copy it into config.py, and change it
    there.

'''

from os.path import dirname
from os import environ

SECRET_KEY = environ.get('SECRET_KEY', 'dev-default-key-change-in-production')
CSRF_ENABLED = True
DATABASE_FILE = environ.get('DATABASE_FILE', 'database.db')

# Logging level for the application. One of: DEBUG, INFO, WARNING, ERROR.
# Override with the LOG_LEVEL environment variable.
LOG_LEVEL = environ.get('LOG_LEVEL', 'INFO')

# The known, insecure default. The app refuses to start in production mode
# (MODE='production') if SECRET_KEY is left at this value.
DEFAULT_INSECURE_SECRET_KEY = 'dev-default-key-change-in-production'

# How many consecutive failed logins before an account is locked out:
MAX_FAILED_LOGINS = 10

# Refuse to accept file uploads bigger than this:

MAX_CONTENT_LENGTH = 1024 * 1024 * 1024 # 1GB. reasonable for video uploads.

# should change some logging settings, etc.  Currently changes very little:

MODE = 'production'

# in minutes.  Usually you'll want to change this by a multiple of 60,
#              so TIME_OFFSET=60 means server time +1 hour,
#                 TIME_OFFSET=-120 means server time -2 hours, etc.

TIME_OFFSET = 0

# Connected display clients (see the admin "Connected Clients" page):
# how often each screen sends a heartbeat, and how long a client may be
# silent before it is considered offline.
SCREEN_HEARTBEAT_INTERVAL = 10  # seconds between heartbeats
SCREEN_CLIENT_TTL = 30          # seconds before a silent client is offline

# Number of reverse proxies chained in front of StreetSign that append
# X-Forwarded-For / set X-Forwarded-Proto (e.g. nginx, nginx-proxy-manager,
# a Docker ingress). Werkzeug's ProxyFix is applied with this hop count, so
# request.remote_addr and request.scheme reflect the real client and protocol.
#
# 0 (default) means "not behind a proxy" and forwarded headers are ignored.
# Set it to exactly the number of proxies in front of StreetSign (1 for a
# single nginx-proxy-manager). Only set this if the app is genuinely behind
# those proxies: trusting forwarded headers from an untrusted client lets it
# spoof its address (which also affects login rate limiting).
TRUSTED_PROXY_HOPS = int(environ.get('TRUSTED_PROXY_HOPS', '0'))

# These are available in all templates, so useful for storing configuration
# strings, etc.

SITE_VARS = {
    'site_title': 'StreetSign',
    'site_dir': dirname(__file__),
    'user_dir': dirname(__file__)+'/streetsign_server/static/user_files/',
    'user_url': '/static/user_files',
    }
