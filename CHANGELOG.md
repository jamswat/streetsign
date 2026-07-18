# Changelog

## v1.3.3 — Alias Bug Fixes & Dashboard Improvements

### Bug Fixes — Aliases

- **CSRF blocks alias saves (CRITICAL)** — `POST /aliases` (`save_aliases`
  endpoint) was missing from the CSRF exempt list. The alias editor sends a
  jQuery `$.post()` without a `_csrf_token`, so every save attempt was
  silently rejected with 403. Added `'save_aliases'` to the exempt list.
- **Silent layout fallback** — when an alias referenced a screen that had
  been deleted or renamed, `makeAliasesEditor` silently swapped to
  `screenNames[0]` with no warning. The original name is now preserved and a
  visible red warning badge is shown in the editor when the screen no longer
  exists.
- **Dashboard 500 with orphaned aliases** — when a screen referenced by an
  alias is deleted, `alias['screen']` becomes `None`. The dashboard template
  accessed `client.screen.background` without a null guard, crashing with
  `AttributeError`. Added `{% if client.screen and client.screen.background %}`.
- **Empty alias names bypass duplicate check** — the list comprehension
  filtered out empty/whitespace names before the dedup check, so two aliases
  with empty names resulted in `names = []` and `0 != 0` passed validation.
  Empty names are now explicitly rejected with a 400 error.

### Bug Fixes — Other

- **Image post crash on missing file** — `image.receive()` raised a bare
  `AssertionError` (500) when no upload/URL/localpath was provided. Now
  flashes a descriptive message and returns empty filename, matching the
  IOError pattern used elsewhere. (`c4fa9fc`)
- **Broken thumbnail images** — broken image post thumbnails (deleted or
  inaccessible files) now gracefully self-remove via `onerror="this.remove()"`
  instead of showing a broken image icon.
- **`streetsign_server.models` wheel packaging** — models package was missing
  from `pyproject.toml` `[tool.hatch.build.targets.wheel.packages]`, which
  would cause `ModuleNotFoundError` on pip-installed releases. Fixed.

### Dashboard

- **Recently Published card** — renders the 5 most recent published posts
  alongside the existing "My Posts" section on the admin dashboard.
- **Expiry/status badges** — "My Posts" table rows now show expiry badges
  (expiring-soon / expired) so stale content is visible at a glance.
- **Active-only filter** — "My Posts" defaults to showing only active posts,
  with a "Show All" toggle to include expired/scheduled posts.
- **Dead queries removed** — unused `total_posts` and `unpublished_posts`
  queries removed from the dashboard view (never passed to template).

### New Features

- **IP-based login rate limiting** — 5 failed login attempts per 60 seconds
  per IP address triggers a temporary block, returning a 429 response. The
  existing per-user account lockout (10 failed attempts) still applies.
- **Post thumbnails in lists** — `Post.repr()` now renders a thumbnail image
  for image posts and a type-specific icon for all post types (text, HTML,
  weather, etc.) in post lists across all views (all posts, feed, dashboard,
  user). Unknown types fall back to a generic file icon.
- **Fuzz test suite** — the standalone fuzz script (`scripts/dev/fuzz.py`)
  has been migrated into the pytest test suite as `tests/test_fuzz.py` with 84
  tests organised across 14 classes using a module-scoped seeded DB fixture.
- **Static asset caching** — WhiteNoise now serves static files with
  `Cache-Control: public, max-age=86400` (24 hours), up from the default
  60 seconds. Screen config-MD5-triggered reloads bypass the cache, so
  updates are picked up immediately while normal operation benefits from
  fewer redundant requests.

### Maintenance

- **Pylint score improved from 9.19 to 9.58** — added missing docstrings,
  wrapped over-long lines, removed unnecessary parentheses, fixed trailing
  blank lines, and added Peewee-specific suppressions for false positives.
  (12 files touched, no behavioural changes.)

## v1.3.2 — Display Performance & Feed Permission Display

### Performance — Display Screen Rendering
- **Weather widget compositing** — removed `backdrop-filter: blur()` from metric
  and forecast cards, and `filter: blur()` from the atmosphere overlay. These
  forced expensive GPU re-compositing on every frame during fade transitions,
  causing stutter on screens with weather + image slideshow zones. Cards now use
  a slightly more opaque flat background.
- **Weather `_fit()` optimised** — added zone-size caching so `_fit()` only
  re-measures when dimensions change; content refreshes still trigger re-fit
  correctly. Cap reduced from 22 to 14 iterations. Duplicate delayed-fit
  call at init removed. Countdown timer interval increased from 1s to 10s.
- **Font auto-fit de-thrashed** — `reduce_font_size_to_fit()` now resizes images
  once after the binary search instead of every iteration, and uses native DOM
  size reads instead of jQuery.
- **Post-fetch waterfall** — new posts from poll responses are now fetched with
  a concurrency cap (4 in flight) and added via `requestAnimationFrame` batching
  instead of all firing at once.
- **Fade-time format bug fixed** — inline transition style now correctly
  constructs e.g. `opacity 1.000s` for fadetime=1000 instead of the broken
  `opacity 0.1000s` (=0.1s). `updatePost` content-swap delay now respects
  the configured fadetime instead of a hardcoded 1000ms.
- **`notrans` scroll rewritten** — replaced `requestAnimationFrame` loop
  animating `style.left` (layout-triggering, no GPU acceleration) with a CSS
  `@keyframes` + `transform: translateX(...)` animation matching `basic.js`.
  Stylesheet is now cleaned up when the scroll post hides.
- **`will-change: transform`** added to `.zone_scroll .post` for GPU layer
  promotion.
- **`web_hook` display/hide** — replaced jQuery `fadeOut()/fadeIn()` on the
  entire `#zones` container with a CSS opacity transition.
- **Dead CSS removed** — `.post.faded_in` rules (class never applied by JS).

### Feed Permission Display
- **Feed view now shows effective permissions** — the read-only Authors and
  Publishers lists on a feed page include users who gain access via group
  membership, not just those with explicit per-user permissions. Duplicate
  entries (user with explicit + group-derived access) are merged to a single
  entry. Admin permission form still uses explicit-only lists for editing.

## v1.3.1 — Weather Overhaul, Bulk Upload & Scheduling Fix

### Weather Post Type Overhaul
- **Text auto-scaling rewritten** — the binary-search fit function now correctly
  measures content height by temporarily relaxing grid constraints (height:auto,
  cell overflow:visible, atmosphere hidden). Previously grid cells with
  `overflow:hidden` collapsed to 0px height, making content invisible and
  `scrollHeight` report no overflow. Font sizes now scale properly from ~20px
  to ~100px depending on content and zone dimensions.
- **Per-metric toggles** — 10 individual metric checkboxes (feels-like, humidity,
  wind speed, wind direction, UV, cloud cover, pressure, visibility,
  precipitation, sun times) replacing the old single show_metrics master switch.
- **Appearance controls** — font sizing mode (auto-fit/manual), layout mode
  (auto/landscape/portrait/square), metrics style (cards/inline pills), and
  refresh status position (header/corner/hidden) with configurable colors.
- **Live preview** — new preview panel in the editor with drag resize, aspect
  ratio buttons, and real-time form-change reflection.
- **Metric card fixes** — cards widened (50% flex-basis), font sizes reduced
  (label 0.55em, value 0.90em), `overflow:hidden` added to contain text within
  card boundaries.

### Bug Fixes
- **Post scheduling silently broken** — flatpickr's `s` format token produced
  seconds without leading zeros (`12:30:0` instead of `12:30:00`), causing the
  DATESTR regex to reject every calendar-picked date. `getstr()` fell back to
  the one-week default. Fixed by using flatpickr's `S` token (2-digit-padded
  seconds). Added client-side validation that blocks submission on malformed
  dates and shows Bootstrap `is-invalid` feedback.
- **Appearance controls had no effect on preview** — HTML IDs used hyphens
  (`weather-layout-mode`) while `readFormConfig` built lookups with underscores
  (`weather-layout_mode`). `getElementById` returned null for all five
  appearance controls. Changed all IDs to use underscores matching config keys.
- **Metric All/None toggles didn't update preview** — jQuery `.prop()` doesn't
  fire DOM events, so the delegated change handler never saw the update. Added
  `.trigger('change')`.
- **Dead code removed** — orphaned `receive()` and `renderer_js()` wrapper
  functions in `post_types/__init__.py` and `external_source_types/__init__.py`.
- Fixed `external_webpage` module docstring referencing wrong module name.

### New Features
- **Bulk image upload** — new `/feeds/<id>/bulk_upload` page with shared
  scheduling (lifetime, time restrictions, recurrence), drag-and-drop, preview
  grid, and per-image custom titles.
- **Screen performance fixes** — reduced `isOnline` divergence in weather
  widget, fixed weather resource leaks (timers, ResizeObserver, listeners).
- **Fuzz/regression test script** added under `scripts/dev/`.

### Documentation
- **ARCHITECTURE.md** — comprehensive project architecture document covering
  technology stack, route map, DB schema, authentication, plugin systems,
  screen rendering pipeline, and key design decisions.

## v1.3.0 — Weather Post Type & Bug Fixes

This release adds a live weather display post type powered by wttr.in, plus
build/CI and bug fix improvements.

### New Features
- **Weather post type** — displays live current conditions, high/low temperatures
  and rain chance, optional metrics (feels-like, humidity, wind, UV), sunrise/sunset
  times, and a 2-day forecast. Zone-size-aware CSS-Grid layout adapts between
  landscape, square, and portrait signage zones. Features:
  - Place name lookup or exact latitude/longitude coordinates with a built-in
    OpenStreetMap coordinate picker.
  - Celsius/Fahrenheit, configurable refresh interval, customisable colours.
  - Weather-aware atmospheric gradients and ambient condition icon (toggleable).
  - Client-side caching (localStorage + memory) with stale-while-revalidate.
  - Expoential backoff for fetch retries and offline detection.
  - Server-side `/weather-proxy` route to relay wttr.in requests (avoids CORS/CSP).

### Bug Fixes
- **Weather widget resource leak** — timers, ResizeObserver, and online/offline
  listeners were never cleaned up when the weather post was re-rendered
  (e.g. on content update). Added `destroy()` lifecycle method and proper
  teardown in `render()`.
- **Weather night detection timezone mismatch** — `_isNight` now uses the
  location's observation time (from `localObsDateTime`) instead of the
  browser's local clock for sunrise/sunset comparison.
- Fix `isOnline` divergence in weather widget — use tracked `this.isOnline`
  instead of `navigator.onLine` in the fetch path.
- **Uncaught `IntegrityError` in deletion paths** — feed, screen, and user
  deletion now handles DB constraint violations gracefully instead of
  returning 500 errors.
- **Build & CI** — pinned `setup-uv` to v8.3.0 for Node 24 compatibility;
  added license files and updated attribution docs for bundled libraries.

### Changes
- Tagged Docker image reference in `docker-compose.yml` changed to `:latest`.

## v1.2.0 — Build System Modernization & CI Fixes

### Build System
- **Migrated from `setup.py` + `requirements.txt` to `pyproject.toml` + `uv.lock`.**
  - `pyproject.toml` (hatchling backend) is now the single source of truth for
    project metadata and dependencies.
  - `uv.lock` pins the entire dependency tree (including transitive deps) for
    fully reproducible builds.
  - `setup.py`, `requirements.txt`, `requirements_raw.txt`, and `MANIFEST.in`
    removed.
  - Runtime deps use compatible-release ranges (`>=X,<Y`); the lockfile pins
    exact versions. `uv lock --upgrade` bumps everything; `uv lock --upgrade-package
    <name>` bumps one package.
  - Dev/test deps (`pytest`, `coverage`, `pylint`, `html5lib`) moved to
    `[project.optional-dependencies] dev` — no longer installed in the Docker
    production image (17 packages instead of 32).
  - Virtualenv directory renamed from `.virtualenv` to `.venv` (uv convention).
- **Dockerfile** updated to use `uv` from `ghcr.io/astral-sh/uv` with
  `uv sync --frozen --no-dev --no-install-project`.
- **Makefile** updated to use `uv sync --extra dev`.
- **CI workflows** updated to use `astral-sh/setup-uv@v6`, `uv sync`, and
  `uv run` for all steps. pip-audit now runs against `uv export --no-dev
  --no-emit-project` output.

### Bug Fixes
- **`markupsafe`** added as an explicit dependency (was a hidden transitive
  dependency via Flask/Jinja2/Werkzeug, but directly imported in 4 application
  files).
- **`bleach[css]`** — added the `[css]` extra for `tinycss2`, required by
  `bleach.css_sanitizer.CSSSanitizer` in the HTML post type. This was a
  pre-existing bug that would break on fresh installs.
- **`whitenoise`** was in `requirements.txt` but missing from
  `requirements_raw.txt` (sync issue eliminated by the single-source
  `pyproject.toml`).
- **Fixed broken `make .githooks` target** — `.setup/hooks/pre-commit` never
  existed. Created a pre-commit hook that runs pylint (fail-under=9.0).

### CI Fixes
- Fixed docs build: `sphinx-build` not found — now uses `uv run make` so the
  venv is on PATH.
- Fixed pip-audit: `uv export` included `-e .` (editable) which breaks
  hash-based auditing. Added `--no-emit-project` to exclude it.
- Bumped GitHub Actions to Node.js 24-compatible versions
  (`actions/checkout@v5`, `actions/setup-python@v6`,
  `actions/upload-pages-artifact@v4`, `actions/deploy-pages@v5`).

### Other
- Added Python 3.14 classifier to `pyproject.toml`.
- Updated all `.virtualenv` → `.venv` references in shebangs, docs, README, and
  scripts.

## v1.1.0 — Operational Improvements & New Features

### Breaking Changes
- Python 3.9 dropped; minimum is now Python 3.10.

### New Features
- **Day-of-week scheduling recurrence** — posts can be limited to specific
  weekdays (e.g. "only show on Mon, Wed, Fri") within their lifetime.
- **Playlist ordering** — admins can reorder posts within a feed via
  up/down arrow buttons on the feed page; display clients cycle posts
  in sort order instead of insertion order.
- **Health endpoint** — lightweight `/health` endpoint that probes the
  database with `SELECT 1` and returns JSON status. Docker HEALTHCHECK
  updated to use it.
- **Database backup script** — `scripts/backup_db.py` uses the SQLite
  online backup API for WAL-safe snapshots while the server runs. Added
  `make backup` target.
- **Configurable logging** — `LOG_LEVEL` config option / env var;
  `print()` calls replaced with `app.logger` / `logging` throughout.

### Security Fixes
- Fixed open-redirect via `request.referrer` on login and other views.
  Added `safe_referrer()` helper that validates same-origin before
  redirecting.
- Fixed invalid nginx reverse-proxy config syntax
  (`proxy_set_header $host;` → `proxy_set_header Host $host;`) and
  added standard proxy headers + `client_max_body_size`.

### CI
- Added GitHub Actions workflow for tests (Python 3.10 + 3.12 matrix),
  pylint (fail-under=9.0), and pip-audit for known CVEs.
- Added `python_requires='>=3.10'` to project metadata.

### Migrations
- Migration 4: add `sort_order` column to Post (playlist ordering).
- Migration 5: add `recurrence` column to Post (day-of-week scheduling).

## v1.0.3 — UI/UX Overhaul

### Bug Fixes
- Fixed double "X" delete button on group list (btn-close + &times; conflict).
- Fixed stray `}` in post editor template output.
- Fixed broken "Full Preview" link for unsaved screens.
- Fixed raw HTML editor: syntax highlighting now constrained to textarea.
- Fixed `.hidden` → `.d-none` in HTML post type color toggle (Bootstrap 5).
- Fixed image upload preview (was commented out — now live on file selection).
- Fixed post type AJAX error handling (shows alert instead of infinite spinner).
- Fixed 403 page: uses styled error template instead of raw HTML.
- Fixed feed.html: removed dead JS targeting non-existent DOM elements.
- Fixed bulk delete: native `confirm()` → Bootstrap modal.
- Fixed Save & Publish: inline `onclick` → proper event listener.
- Fixed `<input type="submit" class="btn-close">` → `<button>` (browser text leak).
- Fixed font-family dropdown: shows "(browser default)" instead of blank.
- Fixed time restriction defaults: `00:20` → `00:00`, `23:30` → `23:59`.
- Fixed `reload_page()` exponential timer leak (setTimeout → setInterval).
- Fixed missing viewport meta on screen display templates.
- Fixed `..` parent link double-click (trailing slash in path computation).
- Fixed screen/alias name spaces: auto-replaced with hyphens.
- Fixed RSS form: Bootstrap 3 → 5 class names.
- Fixed hidden "Other Settings" textarea: now `<input type="hidden">`.
- Fixed group editor title from "Userlist" to group name.
- Fixed non-admin group view: bare table → styled Bootstrap table.

### File Browser Redesign
- Drag & drop upload zone with per-file progress bar.
- Sortable columns (name, type, size, date).
- Bulk delete with checkboxes and floating action bar.
- Breadcrumb navigation for subdirectories; `..` parent row.
- Filename always shown alongside thumbnail.
- New columns: Type badge (Image/Font/Video), Modification Date.
- Font-family name hint badge for font files.
- File count summary.
- Font preview button (renders sample text in the actual font).
- Video format support (MP4, WebM, Ogg, MOV) via upload to `videos/`.
- Upload input renamed from `image_file` to `file`.

### Post & Form Improvements
- Time restrictions highlighted yellow when start ≥ end.
- Housekeeping button: tooltip explaining what housekeeping does (posts page).
- External source Test / Run Now: loading skeletons and error handling.
- Login modal: `data-bs-backdrop="static"` to prevent accidental dismiss.
- Dashboard: feed name badge on My Posts entries.

### Video Post Type
- Toggle between "Upload new" and "Choose from uploaded files".
- Browser-shared videos not deleted when post is removed.

### Accessibility
- Alias checkbox wrapped in `<label>`.
- Error page footer hidden.

## v1.0.2 — Docker Build Fix

- Fixed Docker build by removing obsolete imagemagick sub-packages.

## v1.0.1 — UI Fixes, Deployment Improvements, and Branding

- Added brand logos (favicon, sidebar, mobile header, landing page).
- Fixed multiple UI validation issues across forms.
- Improved docker-compose.yml: configurable port, SECRET_KEY safety, clearer docs.
- Updated documentation to reference ghcr.io pre-built Docker images.
- Pinned and bumped GitHub Actions to latest versions.
- Pylint cleanup and logo integration.
- Robustness improvements across post and feed views.

## v1.0.0 — Initial Rewrite/Modernization

This release marks the initial fork and modernization of StreetSign.
Many, many changes including:
- Bootstrap 3 -> 5
- Move from Knockout.js -> Alpine.js
- Various library updates
- Many bug fixes and security improvements
- UI improvements
- Move to Quill WYSIWYG for rich text
- Add Video post type
- Add raw html post type
- Remove Twitter & Advanced html post types
