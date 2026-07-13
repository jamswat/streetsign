# TODO

## Bugs

- [ ] `streetsign_server.models` is missing from `pyproject.toml` wheel packages — wheel installs would fail on `from streetsign_server.models import ...`

## Dashboard Improvements

### Tier 1 — Low effort, immediate payoff

- [ ] Remove unused `total_posts` and `unpublished_posts` queries from `views/__init__.py:112-113` (dead code — never passed to template)
- [ ] Render already-queried `recent_posts` in a "Recently Published" card alongside "My Posts" on the admin dashboard
- [ ] Add expiry badges (expiring-soon / expired) to "My Posts" table rows so stale content is visible at a glance
- [ ] Filter "My Posts" to show only active posts by default, with a "Show All" toggle

### Tier 2 — Moderate effort

- [ ] Add a "Posts Expiring Soon" stat card showing posts active now but ending within 48 hours
- [ ] Replace full-size screen background images in the Public Screens section with thumbnails (reuse existing `/thumbnail/` endpoint)
- [ ] When screen uses no background, have a basic preview of the zones.
- [ ] Clean up "My Feeds" table layout — remove per-row "New Post" button noise, show feed name + post count instead

### Tier 3 — Larger changes

- [ ] Role-aware stat cards — admins see user counts, storage usage, external source health; authors see their own stats; non-admins don't see system-wide Feed/Screen counts
- [ ] External data source status on admin dashboard (last checked timestamp, success / failure indicator)
- [ ] Screen preview thumbnails — generate small thumbnails of screen layouts for the Public Screens section instead of loading full background images

---

## General

### High impact

- [ ] Server-side pagination and search for `/posts/` — `Post.select()` loads every row, problematic at scale
- [ ] Audit trail — log who published, edited, deleted, or moved a post; who changed screen layouts; who modified permissions

### Medium impact

- [ ] Display preview — embed a live preview of a screen layout in the screen editor (iframe or canvas-based) (only for images I think - raw html, weather, video etc. are not practical or accurate at small scale)
- [ ] Emergency override / immediate push — push urgent full screen content to all screens temporairilly.
- [ ] Screen grouping / tags — label screens by location, department, or type for bulk operations
- [ ] Image content resizing for specific zones — serve scaled images for low-resolution zones to save bandwidth (generate more sizes with imagemagick)
- [ ] Generate video thumbnails
- [ ] Database maintenance / cleanup job — prune expired sessions, orphaned user files, and stale post data
- [ ] Bulk post operations — bulk delete, archive, publish/unpublish

### Low impact

- [ ] Post expiry notifications — alert authors before their posts expire
- [ ] Drag-drop zone layout editor — visual zone positioning instead of form fields
- [ ] i18n / l10n support — currently English-only
- [ ] Rate limiting on login — brute-force protection beyond the existing account lockout (10 failed attempts)
- [ ] Calendar view for post scheduling — timeline / calendar UI to visualize and manage many time-scheduled posts
- [ ] Content Security Policy hardening — tighten CSP headers beyond existing security headers
- [ ] JavaScript tests — currently no JS test harness; screen rendering and admin UI JS are untested
- [ ] External source type tests — RSS importer and local folder image importer have no test coverage
- [ ] Weather proxy endpoint tests — `/weather-proxy/` has no dedicated functionality or SSRF-safety tests
- [ ] Screen rendering integration tests — no test exercises the full display JSON pipeline (`/screens/json/`, `/screens/posts_from_feeds/`)
