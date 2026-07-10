# Changelog

## v1.1.0 — Operational Improvements & New Features

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
- Added GitHub Actions workflow for tests (Python 3.9 + 3.12 matrix),
  pylint (fail-under=9.0), and pip-audit for known CVEs.
- Added `python_requires='>=3.9'` to `setup.py`.

### Migrations
- Migration 4: add `sort_order` column to Post (playlist ordering).
- Migration 5: add `recurrence` column to Post (day-of-week scheduling).

## v1.0.0 — Initial Rewrite/Modernization

This release marks the initial fork and complete modernization of the StreetSign
digital signage server, incorporating extensive security hardening, library
upgrades, accessibility improvements, and new features.

## v1.0.1 — UI Fixes, Deployment Improvements, and Branding

- Added brand logos (favicon, sidebar, mobile header, landing page).
- Fixed multiple UI validation issues across forms.
- Improved docker-compose.yml: configurable port, SECRET_KEY safety, clearer docs.
- Updated documentation to reference ghcr.io pre-built Docker images.
- Pinned and bumped GitHub Actions to latest versions.
- Pylint cleanup and logo integration.
- Robustness improvements across post and feed views.

## v1.0.2 — Docker Build Fix

- Fixed Docker build by removing obsolete imagemagick sub-packages.

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
- Housekeeping button: loading state and error feedback.
- External source Test / Run Now: loading skeletons and error handling.
- Login modal: `data-bs-backdrop="static"` to prevent accidental dismiss.
- Dashboard: feed name badge on My Posts entries.

### Video Post Type
- Toggle between "Upload new" and "Choose from uploaded files".
- Browser-shared videos not deleted when post is removed.

### Accessibility
- Alias checkbox wrapped in `<label>`.
- Error page footer hidden.