StreetSign Admin's guide
========================

Here's first a guide on how to set up streetsign to play with.  For full proper
deployment (for real live production usage) check the :doc:`deployment` page.

Installation
------------

StreetSign requires python 3.10+, imagemagick (to generate thumbnails).  If you
are installing on a fresh server, you may need to install ``python3-headers``
or ``python3-dev`` or whatever your distribution calls it.

(On a stock OSX computer, it doesn't need anything.)

Once you've cloned or otherwise downloaded StreetSign and put it where you
want it to be, you need to run the setup script::

    ./setup.sh

which will create a python virtualenv in ``.virtualenv``, and install all the
libraries and other requirements into there (via the ``Makefile``).

Running it.
-----------

To run the server in 'production mode' you can use the built in ``waitress`` web server::

    ./run.py waitress

In production mode the server **refuses to start if ``SECRET_KEY`` is still the
insecure default** — set a unique random value (see below) before deploying.

Which will spin up a version which should be totally capable for small
deployments (up to a hundred screens or so, I guess).  If you are going to be
on a public network, then it's advised that you run streetsign - either with
waitress or another WSGI server of your choice - behind nginx or another
reverse proxy, which should keep things a bit saner.  If you're on a public
network, also remember to set up your reverse proxy to use SSL, so that you
aren't sending log-in credentials around in plaintext.

Static files are served in-process by WhiteNoise_, so no separate web server
or reverse proxy is required for static assets.

If you want to run another WSGI server, remember the virtualenv that streetsign
is using, so any scripts you write need to use the python found in there
(``.virtualenv/bin/python``).  You can use pip from in there to install any
pypi packages you need too (``.virtualenv/bin/pip install gunicorn``, say).

If you want to run the bare development server (not for production) you can run
``./run.py`` with no argument. The interactive Werkzeug debugger is **off by
default**; if you opt in with ``FLASK_DEBUG=1`` the server binds only to
``127.0.0.1``, because the debugger exposes a remote code-execution console.

Some links:
~~~~~~~~~~~

- `The official flask deployment docs <https://flask.palletsprojects.com/en/stable/deploying/>`_
- `The waitress server docs <https://docs.pylonsproject.org/projects/waitress/en/stable/>`_


Users
-----

When you first install, the database is seeded with three demo users for you.
The password for each one matches its login name, so:

- ``admin`` / ``admin`` — a full administrator (in the ``admins`` group)
- ``editor`` / ``editor`` — can write and publish on all feeds (in the
  ``editors`` group)
- ``viewer`` / ``viewer`` — read-only

**Change these passwords as soon as possible**, especially ``admin``.

Because some things display differently for admins compared to 'normal' users,
the pre-created ``editor`` and ``viewer`` accounts are handy for checking how
the interface looks for non-admins.

Account lockout
~~~~~~~~~~~~~~~

To slow down password-guessing, an account is automatically locked out after a
number of consecutive failed login attempts (``MAX_FAILED_LOGINS``, default
``10``). A locked-out account cannot log in until an admin clears the lock from
the user's edit page.

Password hashes and moving the database
---------------------------------------

User passwords are stored hashed with bcrypt (each with its own per-password
salt). Before hashing, the password is run through SHA-256 so that passwords
longer than bcrypt's 72-byte limit are fully used. The password hashes are
**independent of** ``SECRET_KEY`` — you can rotate ``SECRET_KEY`` without
locking anyone out, and you can move a ``database.db`` file between
installations without needing to copy the ``SECRET_KEY``.

``SECRET_KEY`` is still important: it signs Flask session cookies, so it must
be set to a long random value in ``config.py`` or via the environment, and
should NEVER be committed to a repository or shared outside the deployment. The
server refuses to start in production if it is left at the insecure default.

Housekeeping & removing old content
-----------------------------------

By default, streetsign will tag content that has a lifetime which ended over a week
ago as "archived".  This means it no longer shows up on the interface for anyone
except admin users.  After a month, it will be deleted, including any uploaded images.

This "housekeeping" should take milliseconds to run as long as it's run regularly,
so each screen view will fire a request to the server to do it once an hour or so.
It and can also be triggered through the interface by hitting the "housekeeping"
button on the "All Posts" page, or on the front page (Dashboard).

If you want to ensure that this runs every hour or so, you can use standard unix
cron, or any other task scheduling program.

- ``HTTP POST`` to ``/posts/housekeeping``

so if you're using cron::

    0 * * * * nobody curl -d "" 'http://streetsign_url/posts/housekeeping' > /dev/null

should do it.

For automatically updating content from external feeds, again, screen views will
automatically do this once a minute, but you can also trigger it manually
(or via cron) with a

- ``HTTP POST`` to ``/external_data_sources/``

If you are on a public network, and worry about DOS issues, then realistically,
you should be running behind a reverse proxy such as nginx.  With nginx you can
add restrictions on what URLS are accessble by any IP address, so you can limit
these addresses to only be accessed by the machine with cron, for instance.

Server Time
-----------

You may well have your main server running in one timezone (say GMT), but actually
be using the signs in another time zone.  By default, clients will all use their
own local time zone, and the server uses the server time.  There is a configuration
option you can set in ``config.py``::

    TIME_OFFSET=60

for example, which will offset post lifetimes, etc, by an hour.  (Minutes are used
so that half-hour-off timezones are supported).

Configuration Reference
-----------------------

All configuration options can be set in ``config.py`` (do not edit
``config_default.py``). See ``config_default.py`` for the full list of defaults.
Key options:

- ``SECRET_KEY`` — Flask session signing key. Must be set to a unique random
  value in production; the server refuses to start if left at the insecure
  default. No longer used for password hashing, so it can be rotated freely.
- ``DATABASE_FILE`` — path to the SQLite database (default: ``database.db``)
- ``TIME_OFFSET`` — timezone offset in minutes (default: ``0``)
- ``MODE`` — ``'production'`` or ``'development'`` (default: ``'production'``)
- ``CSRF_ENABLED`` — enable CSRF protection for all state-changing requests,
  including login and logout (default: ``True``)
- ``MAX_FAILED_LOGINS`` — consecutive failed logins before an account is locked
  out (default: ``10``)
- ``MAX_CONTENT_LENGTH`` — max upload size in bytes (default: 1 GB)
- ``LOG_LEVEL`` — logging level for the application (default: ``INFO``).
  One of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``. Can also be set via
  the ``LOG_LEVEL`` environment variable.
- ``SITE_VARS`` — dict with ``site_title``, ``site_dir``, ``user_dir``,
  ``user_url`` for paths and branding

Logging
-------

StreetSign uses Python's standard ``logging`` module. When started via
``./run.py`` (or ``./run.py waitress``), ``logging.basicConfig()`` is
called with a timestamped format at the level given by ``LOG_LEVEL``.
All application messages go through ``streetsign_server`` loggers and
appear on stderr — in Docker they're captured by ``docker logs``, under
systemd by ``journalctl -u streetsign``.

Backup & Restore
----------------

A naïve ``cp database.db`` can produce a corrupt copy because SQLite in
WAL mode also writes to ``database.db-wal``. Use the built-in backup
script, which uses the SQLite online backup API to produce a consistent
snapshot while the server keeps running::

    make backup
    # or explicitly:
    .virtualenv/bin/python scripts/backup_db.py /path/to/backup.db

In Docker, mount a backup volume and run it from cron::

    docker exec streetsign python scripts/backup_db.py /backups/streetsign-$(date +%F).db

To restore, stop the server, replace ``database.db`` with the backup
file, and restart.

Health Check
------------

A lightweight ``/health`` endpoint is available for Docker
``HEALTHCHECK``, load balancers, and monitoring systems. It runs a
``SELECT 1`` against the database and returns JSON::

    {"status": "ok", "database": "ok"}        # 200 OK
    {"status": "error", "database": "unreachable"}  # 503

No authentication is required.

