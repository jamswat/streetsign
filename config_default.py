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

# How to determine the real client IP for display clients. Display clients are
# usually reached through a reverse proxy (nginx, Docker), so the socket peer
# address is the proxy. 'auto' trusts X-Forwarded-For only when the immediate
# peer is a loopback or private address (the common proxy case); True always
# trusts it; False never does. Note: X-Forwarded-For is only used for the
# informational client list, never for authentication.
TRUST_PROXY_HEADERS = 'auto'

# These are available in all templates, so useful for storing configuration
# strings, etc.

SITE_VARS = {
    'site_title': 'StreetSign',
    'site_dir': dirname(__file__),
    'user_dir': dirname(__file__)+'/streetsign_server/static/user_files/',
    'user_url': '/static/user_files',
    }
