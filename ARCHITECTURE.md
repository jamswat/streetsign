# StreetSign Architecture

StreetSign is a digital signage server — a Flask web application that manages
screens, feeds, and posts.  Administrators create content through a Bootstrap 5
web UI; display screens (billboards, kiosks, TVs) poll the server for content
and render it in a web browser using JavaScript-driven transitions.

---

## Directory Structure

```
streetsign_server/            # Main application package
├── __init__.py               # Flask app factory, WhiteNoise, security
├── user_session.py           # Session management (login/logout)
│
├── models/                   # Peewee ORM models
│   ├── __init__.py           # Re-exports, init(), migrations()
│   ├── base.py               # DB connection, utility functions, DBModel
│   ├── users.py              # User, Group, UserGroup
│   ├── auth.py               # UserSession, login/logout
│   ├── feeds.py              # Feed, FeedPermission, Post, ExternalSource
│   ├── screens.py            # Screen
│   └── config.py             # ConfigVar (runtime key-value store)
│
├── views/                    # Flask route handlers
│   ├── __init__.py           # Dashboard, /health, CSRF, error handlers
│   ├── screens.py            # Screen management, display, aliases
│   ├── feeds_and_posts.py    # Feed/Post CRUD, RSS, external sources, bulk upload
│   ├── users_and_auth.py     # Login/logout, user/group management
│   ├── user_files.py         # File uploads, thumbnails, font CSS
│   └── utils.py              # @admin_only, @registered_users_only, helpers
│
├── logic/                    # Business logic (separated from views)
│   ├── feeds_and_posts.py    # post_form_intake, cleanup, external import
│   └── urlsafety.py          # SSRF protection for server-side URL fetches
│
├── post_types/               # Pluggable post type system (8 types)
│   ├── __init__.py           # Discovery, loading, caching
│   ├── text/                 # Plain text (auto-scaled to zone)
│   ├── html/                 # Rich text (Quill editor, bleach-sanitized)
│   ├── image/                # Uploaded images (resize, thumbnail)
│   ├── video/                # HTML5 video
│   ├── weather/              # Live weather from wttr.in
│   ├── web_hook/             # AJAX callbacks on display/hide
│   ├── external_webpage/     # Embedded iframe
│   └── raw_html/             # Unsanitized HTML
│
├── external_source_types/    # Pluggable data importers
│   ├── __init__.py           # Discovery, loading (same pattern as post_types)
│   ├── rss/                  # RSS/ATOM feed importer
│   └── localfolderimages/    # Watch local folder for new images
│
├── templates/                # Jinja2 templates
│   ├── index.html            # Login / redirect page
│   ├── dashboard.html        # Admin dashboard (stats, recent posts, publish queue)
│   ├── error.html            # Error pages (403, 404)
│   ├── screens.html          # Screen listing
│   ├── screen_editor.html    # Screen zone/layout editor
│   ├── screens/              # Screen display templates
│   │   ├── _base.html        # Base screen (all JS/CSS loading)
│   │   ├── basic.html        # Standard (CSS3 fade/scroll transitions)
│   │   ├── mobile.html       # Mobile-optimized
│   │   ├── notrans.html      # No transitions
│   │   └── overview.html     # Multi-screen overview
│   ├── feeds.html            # Feed listing
│   ├── feed.html             # Single feed (permissions, post types, delete)
│   ├── posts.html            # Post listing
│   ├── bulk_upload.html      # Bulk image upload UI
│   ├── postnew.html          # New post creation page
│   ├── post_editor.html      # Post editing page
│   ├── post_editor_form.html # Shared post editor (scheduling/appearance)
│   ├── post_type_container.html # AJAX-loaded post type form wrapper
│   ├── post_types.js         # Jinja2-generated JS for screen post renderers
│   ├── users_and_groups.html # User/group management page
│   ├── user.html             # Single user editor
│   ├── group.html            # Single group editor
│   ├── user_files.html       # File browser and uploader
│   ├── external_source.html  # External data source editor
│   ├── common_widgets.html   # Shared Jinja2 widget macros
│   └── link-macros.html      # Shared link URL macros
│
└── static/                   # Static assets (WhiteNoise-served)
    ├── main.js               # Admin UI JS
    ├── style.css             # Admin UI CSS
    ├── post_editor.js        # Post editor form logic
    ├── post_times_editor.js  # Post time-scheduling editor
    ├── model_zones.js        # Screen zone model editor
    ├── alias_editor.js       # Screen alias editor
    ├── screens/              # Screen rendering JS
    │   ├── globals.js        # Window globals, module containers
    │   ├── functions.js      # safeGetJSON, font scaling, time utils
    │   ├── main.js           # StreetScreen, Zone classes, poll cycle
    │   ├── basic.js          # Zone HTML, fade/scroll transitions
    │   ├── overview.js       # Overview screen layout
    │   ├── notrans.js        # No-transition screen rendering
    │   ├── main.css          # Screen layout and transition CSS
    │   ├── screen-content.css# Post content styling
    │   └── debug.css         # Debug visualisation for screens
    ├── lib/                  # Vendor JS/CSS
    │   ├── bootstrap5/       # Bootstrap 5 (admin UI)
    │   ├── bootstrap-icons/  # Icon set
    │   ├── jquery.js         # jQuery (admin JS + screen legacy)
    │   ├── alpine.js         # Declarative reactivity (Alpine.js)
    │   ├── quill/            # Rich text editor
    │   ├── flatpickr/        # Date/time picker
    │   ├── choices/          # Enhanced select widgets
    │   ├── dayjs/            # Date formatting
    │   └── prism/            # Syntax highlighting
    └── resources/            # Logos, icons, background textures
```

Supporting files:
```
pyproject.toml                # Project metadata, dependencies (Hatchling + uv)
Makefile                      # make all, clean, migrate, backup
run.py                        # Entrypoint (dev server or Waitress production)
db.py                         # DB CLI (seeding, migrations)
config.py                     # User config overrides
config_default.py             # Default config (not to be edited)
Dockerfile                    # Multi-stage Python 3.12 Alpine
docker-compose.yml            # Container orchestration
entrypoint.sh                 # Container entrypoint (migrations + server)
tests/                        # pytest test suite (245 tests)
scripts/                      # Dev scripts (backup, fuzzing, thumbnails)
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | Flask 3.x | HTTP routing, request handling |
| ORM | Peewee 4.x | SQLite database access |
| Templates | Jinja2 3.x | Server-side HTML rendering |
| Passwords | bcrypt 5.x | Password hashing |
| Sanitization | bleach 6.x | HTML content sanitization |
| RSS | feedparser 6.x | External feed parsing |
| WSGI (prod) | waitress 3.x | Production server |
| Static files | whitenoise 6.x | In-process static file serving |
| Editor | Quill | Rich text editing |
| Admin UI | Bootstrap 5 | Layout and components |
| Screen UI | jQuery, Alpine.js | DOM manipulation and reactivity |
| Highlighting | Prism | Syntax highlighting in editors |

---

## Database Schema

All tables use SQLite with Peewee ORM.  WAL journal mode is enabled for
concurrent read/write performance; foreign keys are enforced.

### User
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| loginname | varchar (unique) | Default: `user_<uuid>` |
| displayname | varchar | Default: "New User" |
| emailaddress | varchar | |
| passwordhash | varchar | SHA-256 then bcrypt |
| is_admin | bool | |
| is_locked_out | bool | After MAX_FAILED_LOGINS failures |
| last_login_attempt | datetime | |
| failed_logins | int | Reset on successful login |

### Group
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| name | varchar (unique) | |
| display | bool | Default: True. Hidden groups excluded from UI lists |

### UserGroup (many-to-many)
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| user_id | FK → User | |
| group_id | FK → Group | |

### UserSession
| Column | Type | Notes |
|--------|------|-------|
| id | varchar (PK) | UUID4 |
| username | varchar | |
| user_id | FK → User | |
| login_time | datetime | |

### Feed
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| name | varchar (unique) | Default: `feed_<uuid>` |
| post_types | varchar | Comma-separated allowed post types |

### FeedPermission
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| feed_id | FK → Feed | Indexed |
| user_id | FK → User | Nullable, indexed |
| group_id | FK → Group | Nullable |
| read | bool | Default: True |
| write | bool | Default: False |
| publish | bool | Default: False |

Indexed on `(feed_id, user_id)`.  `group_id` is intentionally not indexed —
group-based lookups are grouped by feed/user first.

### Post
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| title | text | |
| type | text | Post type identifier (e.g. 'html', 'image') |
| content | text | JSON blob — actual content |
| fontsize | int | Nullable (0 = auto) |
| feed_id | FK → Feed | Indexed, backref='posts' |
| author_id | FK → User | Indexed, backref='posts' |
| write_date | datetime | Auto-updates on save |
| published | bool | |
| publish_date | datetime | Nullable |
| publisher_id | FK → User | Nullable |
| status | int | 0=active, 1=finished, 2=archived |
| active_start | datetime | Default: now |
| active_end | datetime | Default: now + 1 week |
| time_restrictions_show | bool | "only show" vs "do not show" mode |
| time_restrictions | text | JSON array of time windows |
| display_time | int | Seconds (0 = permanent), default 8 |
| sort_order | int | Playlist ordering weight, default 0 |
| recurrence | text | JSON `{"enabled":bool, "days":[...]}` |

Indexed on `(status, published, active_start, active_end)`.

### ExternalSource
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| name | varchar (unique) | |
| type | varchar | Source type identifier (e.g. 'rss') |
| frequency | int | Minutes between checks, default 60 |
| last_checked | datetime | Nullable |
| feed_id | FK → Feed | Destination feed |
| settings | text | JSON, type-specific config |
| publish | bool | Auto-publish new posts? |
| post_as_user_id | FK → User | Author of imported posts |
| post_template | varchar | JSON, initial post field overrides (TODO) |
| lifetime_start | varchar | Date formula (e.g. "NOW") |
| lifetime_end | varchar | Date formula (e.g. "NOW + 1 WEEK") |
| display_time | int | Default 8 |

### Screen
| Column | Type | Notes |
|--------|------|-------|
| id | int (PK) | |
| urlname | varchar (unique) | URL slug |
| background | varchar | Nullable, uploaded image filename |
| settings | text | JSON, screen-level settings |
| css | text | Raw CSS injected into page |
| defaults | text | JSON, default zone settings |
| zones | text | JSON array of zone definitions |

### ConfigVar (runtime key-value store)
| Column | Type | Notes |
|--------|------|-------|
| id | varchar (PK) | Config key name |
| value | text | Nullable, stored as JSON |
| description | varchar | |

---

## Route Map

### Public endpoints (no auth)

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/`, `/index.html` | Dashboard (login page if not authenticated) |
| GET | `/health` | Liveness probe: JSON `{status:"ok"}` or 503 |
| GET | `/robots.txt` | Blocks search engine indexing |
| POST | `/login` | Authenticate user, create session |
| POST | `/logout` | Destroy session |
| GET | `/screens/<template>/<screenname>` | Screen display (the actual billboard) |
| GET | `/screens/posts_from_feeds/<json>` | Poll endpoint: JSON list of active posts |
| GET | `/screens/json/<id>[/<md5>]` | Screen config poll (conditional update via MD5) |
| GET | `/screens/post_types.js` | Dynamically generated JS renderers |
| GET | `/feeds/rss/<ids>` | RSS 2.0 feed export |
| GET | `/posts/<id>/json` | Post JSON (only active+published, or auth) |
| GET | `/weather-proxy/<query>` | Proxied wttr.in requests |
| GET | `/client/<alias>` | Screen alias redirect |
| GET | `/user_files/fonts.css` | Dynamic @font-face CSS |

### Registered users

| Method | Route | Purpose |
|--------|-------|---------|
| GET/POST | `/feeds/` | View feeds; admin creates new feeds |
| GET/POST | `/feeds/<id>` | Feed settings; admin edits permissions/delete |
| GET/POST | `/feeds/<id>/bulk_upload` | Bulk image upload with shared scheduling |
| GET/POST | `/posts/new/<feed_id>` | Create new post |
| GET/POST | `/posts/<id>` | Edit post (publish/unpublish/delete/move) |
| GET | `/posts/edittype/<typeid>` | AJAX: load post type editor form |
| POST | `/posts/bulk_delete` | JSON bulk delete |
| GET | `/posts/` | View all posts |
| GET | `/screens/` | View screens |
| GET/POST | `/users/-1` | Create new user (admin only for POST) |
| GET/POST/DELETE | `/users/<id>` | Edit/delete user |
| GET/POST | `/group/<id>` | Edit group; admin changes members/deletes |
| GET/POST | `/users_and_groups` | User/group listing; admin creates groups |
| GET/POST | `/user_files/` | File browser; admin uploads/deletes |
| GET | `/thumbnail/<filename>` | Image thumbnail generation |
| GET | `/aliases` | View screen aliases |

### Admin only

| Method | Route | Purpose |
|--------|-------|---------|
| POST | `/feeds/<id>/reorder` | JSON-based post ordering |
| POST | `/posts/housekeeping` | Archive/delete old posts, cleanup orphaned files |
| POST | `/aliases` | Save screen aliases |
| GET/POST | `/screens-edit/<id>` | Create/edit screen (-1 for new) |
| GET/POST/DELETE | `/external_data_sources/*` | Manage external data sources |
| POST | `/external_data_sources/<id>/run` | Manually run importer |
| POST | `/external_data_sources/test` | Test external source configuration |
| POST | `/external_data_sources/` | Batch run all external sources |

---

## Authentication

### Password storage

Passwords go through a two-stage hashing process:

1. Raw password → SHA-256 → base64 (to fit bcrypt's 72-byte input limit)
2. SHA-256 hash → bcrypt with salt

This means password hashes are independent of `SECRET_KEY` — rotating the key does not invalidate passwords.

### Login flow

1. POST to `/login` with `username` and `password`
2. `user_session.login()` → `user_login()` in `models/auth.py`:
   - Look up User by loginname
   - Check `is_locked_out` flag
   - Verify password (SHA-256 → bcrypt)
   - On success: reset `failed_logins`, create `UserSession` row (UUID4)
   - On failure: increment `failed_logins`, lock out if ≥ `MAX_FAILED_LOGINS` (10)
3. Flask session cookies set: `username`, `userid`, `display_admin_stuff`, `sessionid`, `logged_in`

### Session validation

`user_session.get_user()` checks `logged_in` cookie, looks up the `UserSession` row by UUID + username, verifies user is not locked out.  If validation fails, all session cookies are cleared.

### Authorization decorators

- `@admin_only('POST')` — checks `is_admin == True` for specified HTTP methods
- `@registered_users_only('GET', 'POST')` — checks user is logged in

### CSRF protection

- UUID4 token generated per session, injected into all templates as `csrf_token`
- All POST/PUT/DELETE/PATCH requests verified via form field `_csrf_token` or header `X-CSRF-Token`
- Constant-time comparison (`hmac.compare_digest`)
- Disabled when `TESTING=True` or `CSRF_ENABLED=False`
- Whitelist of public endpoints (screen display, JSON, polling) exempted

### Security headers

`X-Content-Type-Options: nosniff` and `X-Frame-Options: SAMEORIGIN` on all responses, both static (WhiteNoise) and dynamic (Flask `after_request`).

---

## Post Type Plugin System

Post types are the core content abstraction.  Each type defines how content is
edited, validated, rendered on screens, and cleaned up.

### Discovery and loading

`post_types/__init__.py` globs `post_types/*/__init__.py` — each subdirectory
is a post type module.  Eight types are built in: `text`, `html`, `image`,
`video`, `weather`, `web_hook`, `external_webpage`, `raw_html`.

Loading uses `importlib.import_module()` with module caching in `_EDITORS` dict.
Falls back to `text` type on import errors.

### Required interface

Each module must export:

| Function | Signature | Purpose |
|----------|-----------|---------|
| `__NAME__` | string | Human-readable name |
| `form(data)` | `(dict) → str` | Returns HTML for the backend editor form |
| `receive(data)` | `(dict) → dict` | Validates and processes form data, returns content dict (serialized to JSON in `Post.content`) |
| `screen_js()` | `() → str` | Returns JavaScript string defining how to render this type on screen |

Optional:
- `display(data)` — backend preview HTML
- `delete(data)` — cleanup hook (e.g., delete uploaded files)

### How content is stored

Each post type's `receive()` returns a dict; this is serialized to JSON and
stored in `Post.content`.  This means new post types can be added without
schema changes.

### Screen rendering JS

`screen_js()` returns JavaScript that is injected into the global `post_types`
object via `/screens/post_types.js`.  Each type provides:

```js
post_types.<type> = {
    render: function(container, data) { ... return element; },
    display: function(post) { ... },   // optional: called when post becomes visible
    hide: function(post) { ... }       // optional: called when post hides
}
```

### Security

- **html**: Sanitized with bleach (whitelist of tags, attributes, CSS)
- **image**: Validates file extension, SSRF-guards URL downloads, stores with UUID prefix
- **external_webpage**: Validates URL scheme is http(s), renders in iframe
- **raw_html**: No sanitization — scripts pass through. Admin-only in practice.

---

## Screen Rendering Pipeline

This is the path from URL to animated display on a billboard screen.

### 1. Initial page load

Browser requests `/screens/basic/Default`.

- **View**: `screendisplay(template, screenname)` validates the template is in `VALID_SCREEN_TEMPLATES`, looks up `Screen` by urlname, renders `screens/basic.html`
- **Template** (`_base.html`) injects:
  - `SCREEN_DATA` = `screen.to_dict()` (all zones, settings, defaults)
  - `POSTS_URL` = `/screens/posts_from_feeds/` template
  - Loads JS in order: jQuery → dayjs → `globals.js` → `functions.js` → `basic.js` → `main.js` → `post_types.js`
- **JS initialization**: `new StreetScreen($('#zones'), SCREEN_DATA)` creates `Zone` objects, calls `start_zones()` after 2s delay

### 2. Zone construction

Each zone from `SCREEN_DATA.zones[]` is a `<div>` with:
- Absolute positioning (`top`/`left`/`bottom`/`right` from zone definition)
- CSS class `zone_<type>` (fade, scroll, etc.)
- Font-size, color, font-family from zone settings
- `feedsurl` = `/screens/posts_from_feeds/[1,2,3]` (JSON of feed IDs)

### 3. Poll cycle

**Post content poll** (every 10 seconds):
```
safeGetJSON(zone.feedsurl)
  → GET /screens/posts_from_feeds/[1,2,3]
  → {posts: [{id, changed, uri: "/posts/<id>/json"}, ...]}
  → Server filters: status=0, active, published, recurrence check
  → Compares against current posts:
    - New posts: fetch full JSON, call zone.addPost()
    - Changed posts: update content inline, adjust display_time
    - Removed posts: mark delete_me, fade out
```

**Screen config poll** (every 50 seconds):
```
safeGetJSON(/screens/json/<id>/<md5>)
  → If MD5 matches: no change
  → If MD5 differs: reload full page
```

### 4. Post display cycling

- **Fade zones**: CSS `opacity` transitions, `display_time` determines cycle duration
- **Scroll zones**: CSS `@keyframes translateX`, speed computed from content width
- Time restrictions checked via `any_relevent_restrictions()`
- Magic variables (`%%TIME%%`, `%%DATE%%`) filled every 60s using dayjs

### 5. Lifetime

Full page reload every 60 minutes (`REFRESH_PAGE_TIMER`) to prevent memory leaks.

---

## External Source Type Plugin System

External sources import content from outside the system on a schedule.

### Discovery

Identical pattern to post types — subdirectories of `external_source_types/` with
`__init__.py`.  Two types built in: `rss`, `localfolderimages`.

### Required interface

| Function | Signature | Purpose |
|----------|-----------|---------|
| `__NAME__` | string | Human-readable name |
| `form(data)` | `(dict) → str` | HTML for configuration form |
| `receive(request)` | `(request) → dict` | Processes form, returns settings dict |
| `get_new(data)` | `(dict) → list` | Imports new content, returns list of post data dicts |

### RSS

Fetches RSS/ATOM feeds via `feedparser`.  Uses a Jinja2 template for rendering
entries into HTML.  Tracks seen entries by `entry.id` to avoid duplicates.
Sanitizes output with bleach.  SSRF-protected via `check_fetch_url()`.

### Local folder images

Monitors a server-local directory for new image files.  Compares `basename()`
against `current_posts` list.  Creates `image`-type posts via the post type's
local-path import path (copies file into managed `post_images/` directory).

---

## Configuration

### Two-layer system

- **`config_default.py`** — defaults, not user-editable.  Reads environment variables
  for `SECRET_KEY`, `DATABASE_FILE`, `LOG_LEVEL`.
- **`config.py`** — user overrides.  Auto-generated on first setup with a UUID secret key.
  Imports all defaults and overrides selectively.

### Key settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `DATABASE_FILE` | `database.db` | SQLite file path |
| `SECRET_KEY` | dev default (must change) | Flask session signing |
| `CSRF_ENABLED` | True | CSRF token validation |
| `MAX_FAILED_LOGINS` | 10 | Account lockout threshold |
| `MAX_CONTENT_LENGTH` | 1 GB | Upload size limit (for video) |
| `TIME_OFFSET` | 0 | Minutes offset from server time |
| `MODE` | production | Affects some logging/behavior |

### Runtime configuration

The `ConfigVar` model provides a database-backed key-value store accessed via
`config_var(key, default)`.  Used for `screens.aliases`, housekeeping thresholds
(`posts.archive_after_days`, `posts.delete_after_days`), and other administrative
settings.

---

## Key Design Decisions

### JSON-in-TextFields

Post content, screen zones, external source settings, and config vars are all
stored as JSON strings in SQLite `TextField` columns.  This avoids schema
changes when adding new post types or zone properties — the schema stays stable
while the JSON schemas evolve independently.

### Client-side rendering

Display screens are pure HTML + JS + CSS.  The server only sends JSON; the
browser handles transitions, timing, and layout.  This keeps the server
stateless for screen clients and allows each client to adapt rendering to its
own viewport.

### Double polling

Screens poll two endpoints independently:
- Post content changes every 10 seconds (cheap — by-ID lookup)
- Screen config changes every 50 seconds (MD5-conditional — no data transferred if unchanged)

Only the config poll triggers a full page reload.  Post content updates are hot-swapped
inline without disrupting the display cycle.

### Plugin architecture

Post types and external source types use identical discovery patterns:
directory globbing + `importlib` + duck-typed function interface with no base
classes.  Adding a new post type requires only a new directory with
`__init__.py`, `form.html`, and `screen.js` — no changes to core code.

### Peewee ORM + SQLite

Single-file database with WAL journal mode for concurrent read/write
performance.  Foreign keys enforced.  Migration system runs on startup via
`db.py` and the Docker entrypoint.  The ORM uses global state (`models.DB`)
which means tests must rebind models to in-memory databases.

### Security posture

- CSRF tokens on all mutating requests with constant-time comparison
- bcrypt password hashing with SHA-256 pre-hash to avoid bcrypt truncation
- SSRF protection for server-side URL fetches (RSS, image URL download, weather proxy)
- bleach sanitization for user-submitted HTML and external content
- `safe_referrer()` prevents open-redirect attacks on login/logout
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`) on all responses
