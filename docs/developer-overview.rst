StreetSign Developer Documentation
==================================

This contains the documentation for developers, either working
*on* StreetSign, or making plugins/other software to work with it.

It's assumed that you're reasonably familiar with StreetSign the end user web
interface and basic terminology (Post, Feed, Screen, Zone, etc). If not,
see the :doc:`getting_started`

Project Structure Overview
--------------------------

The main "everything" is kept in the folder (& python package)
``"streetsign_server"``, which is a WSGI application, and can be treated as
such. Within ``streetsign_server``:

__init__.py
~~~~~~~~~~~

The basic app definition, which pulls in everything else that it needs,
calls ``models.init()``, and imports all view modules.

models/
~~~~~~~

The ORM database models live in a package with several submodules:

- ``base.py`` — DB connection, utility functions, base model class, custom exceptions
- ``users.py`` — ``User``, ``Group``, ``UserGroup`` classes
- ``auth.py`` — ``UserSession``, login/logout/get_current_user functions
- ``feeds.py`` — ``Feed``, ``FeedPermission``, ``Post``, ``ExternalSource`` classes
- ``screens.py`` — ``Screen`` class
- ``config.py`` — ``ConfigVar`` key-value store

Full Reference: :doc:`developer/models`

user_session.py
~~~~~~~~~~~~~~~

A bunch of helpful functions for dealing with the user session & authentication
stuff.  The basics are kept in the ``User``, ``Group``, and ``UserSession``
objects defined in ``models/``, but the functions here help make life easier
and shorter. The function ``login(username, password)`` for example, attempts
to log in with those credentials, and if it can, then it creates the
appropriate ``UserSession`` database items, and adds useful items to the
session cookie.

Full Reference: :doc:`developer/user_session`

views/
~~~~~~

The views package contains all of the actual "endpoints" of the web
application.  So the functions which generate the pages you see when
you use the web interface, the screen rendering, etc.  It is mostly
split out into submodules.

Full Reference: :doc:`developer/views`

logic/
~~~~~~

The logic package is where more complex logic is being moved to from the
views package.  Once things start becoming more complex than simply pulling
things from the database and rendering it, and the logic is application
specific rather than model specific, then it should go in here.  There is
more logic than really should be in `views/`, and in general, it should
be ported across to here.

Full Reference: :doc:`developer/logic`

static/
~~~~~~~

The standard Flask static assets folder.

static/lib/
```````````
Contains external libraries (jQuery, Alpine.js, Bootstrap 5, Choices.js, Quill,
Flatpickr, Day.js, Prism, Bootstrap Icons).

static/screens/
```````````````
Is for all the css & javascript used by the front end screen rendering.

static/user_files/
``````````````````
Is the default location for uploaded user files.  This can be configured to
some degree in the root of the tree ``config.py``.

static/style.css
````````````````
As much as possible, I've kept with vanilla twitter bootstrap, as it looks
perfectly good enough.  Anything application specific is in here.  Of course,
this is talking only about the web interface, not about the output screen
rendering, which doesn't reference this file at all.

static/main.js
``````````````
All the basic functions which all of the back end needs.  Such as rendering
"flashed" notices, etc.

static/model_zones.js
`````````````````````
The screen editor is a reasonably complex beast, and uses the Alpine.js
library to keep everything sane.  This file contains the zones model and
functions to control it all (creating the preview, etc).
This file is *not used at all* in the output screen rendering.  It's a totally
separate kettle of fish.

static/post_times_editor.js
```````````````````````````
The post time restrictions editing is also a bit fiddly, so all the clobber for
that is kept in here.

static/post_editor.js
`````````````````````
JavaScript for the post editing interface.

static/alias_editor.js
``````````````````````
JavaScript for managing client screen aliases.

Other files in the root directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starting with the file layout:

``run.py`` - run the basic development web server, Waitress stand alone
              WSGI server, or with Werkzeug profiler. The development server's
              interactive debugger is off by default (opt in with
              ``FLASK_DEBUG=1``, which also restricts the bind to 127.0.0.1).
              Usage::

                  ./run.py              # development server (no debugger)
                  ./run.py waitress     # production server
                  ./run.py profiler     # dev server with Werkzeug profiling

``setup.sh`` - downloads all needed python packages, including virtualenv,
               and installs them into a local virtualenv called, very
               creatively, .virtualenv.  Also initialises the database, if
               it doesn't exist.  If you totally stuff up the database,
               then you can simply delete it and run this script again.
               (Now delegates to the ``Makefile``.)

``database.db`` - the sqlite database, generated by ``setup.sh``, normally.

``db.py`` - database management script (initial creation and migrations).

``Dockerfile`` - multi-stage Docker build producing a ~45 MB production image.

API/Urls
--------

Can be found in :doc:`developer/api`

How Post Types work
-------------------

Full Reference: :doc:`developer/post_types`

How External Data Types Work
----------------------------

Full Reference: :doc:`developer/external_source_types`

How the 'Screens' Work
----------------------

Full Reference: :doc:`screen_options`

How Different Libraries are used
--------------------------------

Full Reference: :doc:`external_libs`

Testing & CI
------------

Tests are written with ``pytest`` and live in the ``tests/`` directory.
Run them with::

    .virtualenv/bin/python -m pytest tests/

Code quality is checked with ``pylint``::

    .virtualenv/bin/python -m pylint --fail-under=9.0 streetsign_server/

Dependencies are audited for known CVEs with ``pip-audit``::

    pip-audit -r requirements.txt

Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~

A GitHub Actions workflow (``.github/workflows/tests.yml``) runs these
checks automatically on every push and pull request to ``master``:

- **test** — ``pytest`` on Python 3.10 and 3.12 (matrix)
- **lint** — ``pylint --fail-under=9.0`` on Python 3.12
- **audit** — ``pip-audit`` for known vulnerabilities

A separate workflow (``.github/workflows/docker-publish.yml``) builds
and publishes a Docker image to ``ghcr.io/jamswat/streetsign`` whenever
a tag matching ``v*`` is pushed.
