# Bugs & Breakage

- ~~Fix 6 failing tests~~ — Done: `related_name`→`backref`, Flask 3 route registration, form KeyError fix
- ~~Remove debug `print()` calls left in production~~ — Done
- ~~Add CSRF protection~~ — Done: per-session token, auto-injected into all forms, exempts API/screen endpoints
- ~~Fix bare `except:` clauses that silently swallow errors~~ — Done
- ~~Fix `now()` mixed tab/space indentation at `models.py:80`~~ — Done
- ~~Fix `feed.set_author_groups` deletes `publish` permissions instead of `write`~~ — Done
- ~~Upgrade Peewee `related_name` → `backref`~~ — Done: 7 deprecation warnings → 0

# High Priority

- Split `models.py` (882 lines) into a package: models, auth functions, migrations, utility helpers
- `__init__.py` does too much — DB init in two places (`__init__.py` and `models.py.init()`); needs single path
- Remove dead/commented code:
  - ~~Flask-Peewee admin references in `__init__.py`~~ — Done
  - Commented RSS feed generation code in `feeds_and_posts.py`
  - Commented login attempt counting code in `users_and_auth.py`
- Complete `test_post_image.py` — currently a WIP stub
- ~~Upgrade Peewee `related_name` → `backref`~~ — Done: 7 warnings → 0
- Peewee 4.x `playhouse.migrate` needs SQLiteMigrator imported at module level; currently `MIGRATOR` is a global but `create_all`/`init` don't always set it up correctly if DB is re-created for tests

# Medium Priority

- Thin out the logic layer — views still call `User.select().where(...)` directly
- Prune `# pylint: disable` list — `missing-docstring`, `wildcard-import`, `unused-wildcard-import`
- Replace `db.py` + `run.py` with single `manage.py` script
- Migrate ConfigVar-based screen aliases to a proper database table
- External Data Sources — finish implementation
- API and documentation
- RSS output of feeds (partially implemented, feed generator import is commented out)
- Screen restarting every 6 hours config

# Config / Deployment

- Update Dockerfile from Python 3.8.2 Alpine to 3.12+
- `config.py` way to 'lock' certain users so they can't be deleted
- Make sure user uploaded files have the right path for new projects
- ConfigVar editor for admins
- Default screen when database is first initiated
- Default posts when database is first initiated

# Post / Feed Features

- Post deactivation → archive, and archive/future posts view
- Better uploaded files editor
- Float left/right for images in rich text posts
- Ability to have full-screen URGENT messages
- RSS post count limiter
- HTML page importer (maybe uses md5 or last-changed to detect new posts)
- Way to move posts between feeds
- Templating & defaults for posts
- 'Unarchive' posts
- Rename uploaded post images to `postid-imagename` to avoid conflicts
- Remove old new-post view complexity — choose types in a single view like external data importer
- Better post types API (better error messages, etc.)

# Screen / Display Engine

- WebSocket push instead of polling (every 6s for posts, 50s for screen config)
- Smarter live screen info updating without full page reload
- Better CSS editing for zones and whole-screen
- Direction control for scroller
- Font select on zones
- Non-session auth for API, makes scripting easier
- Local machine mini-proxy for offline resilience
- Urgent alert post type, takes over whole display
- HTML5 video post type
- YouTube video post type
- Sub-zones post type (horizontal/vertical mode with nested zones)

# UI / UX

- Clicking on the text box should open up the time select for post lifetime
- By default, don't show old posts
- Draggable borders in zone editor
- Favicon & other sundries (404, 301 pages, etc.)
- Better image thumbnails
- Default themes
- Validate with html5lib in tests — nice, but HTML5 strict mode may be too aggressive for template rendering quirks

# Future (v2.0+)

- Translation & i18n/gettext
- Better output/client management — status tracking, alert when screens go down
- Separate admin & theme designer roles
- Export/Import screen data (JSON)
- Streetsign 2.0: modular, documented API, plugin marketplace
