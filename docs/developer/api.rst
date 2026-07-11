API/Urls
========

This is a list of the basic API/URLs that streetsign uses, and can be used to
generate other applications (such as a native hardware accelerated client,
for instance.)

All URLs are given in Flask style, so ``<stuff>`` denotes a variable, part
of the URL that changes depending on what you're requesting. ``<int:blah>``
means only accept integer values for ``blah``, etc.

``/health``
-----------

Returns a lightweight JSON health check. Probes the database with
``SELECT 1``::

    {"status": "ok", "database": "ok"}        # 200 OK
    {"status": "error", "database": "unreachable"}  # 503

No authentication is required.  Intended for Docker ``HEALTHCHECK``,
load balancers, and monitoring systems.

``/robots.txt``
---------------

Blocks all well-behaved search engines with ``Disallow: /``.

``/screens/``
-------------

Returns an HTML listing of all screens (requires login).

``/screens-edit/<int:screenid>``
---------------------------------

Screen layout editor.  ``screenid=-1`` creates a new screen.
GET returns the editor page; POST saves or deletes.

``/screens/<template>/<screenname>``
-----------------------------------

Returns the data about this screen, including which zones are defined in it,
which feeds are attached to those zones, etc.  The ``template`` can be one of:
``basic`` (CSS3 transitions, modern browsers), ``notrans`` (low-power devices),
``mobile`` (phones/tablets), or ``overview`` (compact summary).

``/screens/json/<int:screen_id>``
---------------------------------

Returns the JSON details about a screen.  Which zones it has, CSS, which
zones have what feeds attached, etc.

To save bandwidth, you can call:

``/screens/json/<int:screen_id>/<md5sum>``

with the md5 that was previously given in the screen JSON data, and the
server will respond with either ONLY the same MD5sum and screen id, or
else with a new MD5sum, and complete new screen JSON data (and id).

``/screens/posts_from_feeds/<[list,of,feed,ids]>``
--------------------------------------------------

Given a json type list of feed ids (``[1,3,2,9,21]``, say), return the JSON
of all posts which are currently active.

Note that for some web servers/requests/proxy systems, you will have to URL
encode the list.  For example: ``/screens/posts_from_feeds/%5B1%2C2%2C%5D``
rather than ``/screens/posts_from_feeds/[1,2]``.  Most web browsers, and
most good HTTP request libraries should do this automatically for you, however.

``/screens/post_types.js``
--------------------------

Returns all the various JSON renderers that are needed for drawing posts
to a screen zone.

``/aliases``
------------

GET returns the current client alias configuration as JSON.
POST saves a new alias configuration (requires admin).

``/client/<alias_name>``
------------------------

Resolves a client alias to the underlying screen.  Named shortcuts
(configured in the web interface) redirect to the appropriate
``/screens/<template>/<screenname>`` URL with the alias's display
overrides applied.

``/feeds/``
-----------

HTML listing of all feeds (requires login).

``/feeds-edit/<int:feedid>``
----------------------------

Feed editor.  ``feedid=-1`` creates a new feed.

``/posts/``
-----------

HTML listing of all posts, with filtering by feed and status.

``/post-edit/<int:postid>``
---------------------------

Post editor.  ``postid=-1`` creates a new post.  GET returns the editor;
POST saves.

``/posts/<int:postid>/json``
----------------------------

Returns a single post's data as JSON.

``/posts/housekeeping``
-----------------------

Triggers archive/deletion of expired content.  POST only; can be called
from cron or manually.

``/posts/delete_orphaned_media``
--------------------------------

Scans ``post_images/`` and ``post_videos/`` for files with no corresponding
database record and removes them.  POST only, admin-only.

``/post/<int:postid>/publish``
------------------------------

Toggles a post's published state.  POST only.

``/login``
----------

POST to authenticate a user (form fields: ``username``, ``password``).

``/logout``
-----------

POST to end the current session.

``/users/``
-----------

HTML user administration listing (admin-only).

``/users-edit/<int:userid>``
----------------------------

User editor.  ``userid=-1`` creates a new user.

``/groups/``
------------

HTML group administration listing (admin-only).

``/groups-edit/<int:groupid>``
------------------------------

Group editor.

``/user_settings/``
-------------------

Current user's settings page.

``/file_browser/``
------------------

HTML file browser for uploaded images, fonts, and videos.

``/file_browser/<path:subdir>``
-------------------------------

File browser for a specific subdirectory.

``/user_files/<path:filename>``
-------------------------------

Serves uploaded user files (images, videos, fonts, etc.).  Requires a valid
session cookie.

``/thumbnail/<path:filename>``
------------------------------

Serves generated thumbnail images.

