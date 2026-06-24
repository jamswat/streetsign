# StreetSign

A lightweight digital signage server written in Python by **Daniel Fairhead**.
Originally created for [Teenstreet 2013](http://www.teenstreet.de) in Germany,
it has been used at large conferences and in corporate environments since.

Built with Flask, Peewee, Alpine.js, and SQLite — manage content feeds, schedule
posts, and display them on configurable screen layouts with smooth fade and scroll
transitions.

---

## How it works

StreetSign is a self-contained web server. Browsers acting as display clients
load a screen layout from the server, then continuously poll for posts from the
feeds assigned to each zone on that layout. Admins create and publish posts
through a web-based control panel, configure multi-zone screen designs, and
optionally import content automatically from RSS feeds or local image folders.
The server handles scheduling (per-post active windows, time-of-day restrictions),
permissions (read/write/publish per feed, per user or group), and housekeeping
(auto-archive old posts).

## Content types

| Type | Description |
|------|-------------|
| **Plain Text** | Unformatted text, auto-scaled to fill the zone |
| **Rich HTML** | Formatted content via the Quill WYSIWYG editor, sanitised with Bleach |
| **Image** | Uploaded or remote images, displayed with `background-size: contain` |
| **Video** | HTML5 video with loop — muted autoplay by default, tap to enable audio |
| **External Web Page** | Embeds any URL in a full-zone iframe |
| **Web Hook** | POSTs to external URLs on render, display, and hide — designed for controlling stream players (e.g. VLC) or automation systems |
| **Raw HTML** | Arbitrary, unsanitised HTML rendered in a sandboxed iframe |

New post types can be added via a plugin system (`streetsign_server/post_types/`).

## Screen engines

Display clients load one of three rendering engines, selected per client alias:

| Engine | Technology | Best for |
|--------|-----------|----------|
| **basic** | CSS3 transitions (`opacity` for fades, `translateX` for scroll) | Modern browsers, full-featured PCs |
| **notrans** | JavaScript `requestAnimationFrame` for scroll | Raspberry Pi, low-powered devices |
| **mobile** | Lightweight CSS | Phones and tablets |

Each screen layout consists of rectangular **zones** positioned on a background.
Each zone subscribes to one or more feeds and cycles through their posts. Zones
support two transition types:

- **Fade** — posts cross-fade via opacity transitions at configurable intervals
- **Scroll** — posts slide horizontally; longer content scrolls for longer

Zones can be styled per-layout with custom CSS, background images per screen,
user-uploaded fonts (`.ttf`/`.otf`), and per-zone font family and colour overrides.

**Client aliases** map short access keys (like `/client/mainhall`) to a specific
screen + engine combination with display overrides (aspect ratio, fadetime,
scroll speed). This lets different physical displays use different layouts without
changing bookmarks on the clients.

## External data

Posts can be imported automatically from external sources:

- **RSS / Atom** feeds — each entry is rendered through a Jinja2 template,
  sanitised with Bleach, and saved as a Rich HTML post. Supports deduplication
  and configurable update frequency.
- **Local folder (images)** — watches a server-side directory for new image
  files and creates Image posts for each.

Both importers run on a configurable schedule (every N minutes) and can
optionally auto-publish new posts. A test button previews what an importer will
produce. Manual "Run Now" is also available.

## Scheduling

- **Post lifetime** — set start and end dates/times, or mark a post
  "Show permanently" (never expires, never rotates)
- **Time-of-day restrictions** — blackout windows or exclusive windows
  (e.g. "only show between 09:00 and 17:00")
- **Display duration** — how many seconds each post stays visible (2–100s)
- **Per-post font size** — override the automatic zone font scaling with a fixed
  point size
- **Magic variables** — `%%TIME%%` and `%%DATE%%` in posts update live on screen

## Permissions

Three permission levels per feed, assignable to users and groups:

- **Read** — view posts in the feed
- **Write** — create and edit posts
- **Publish** — mark posts as ready for display (separate from write — the
  dashboard highlights unpublished posts)

Admins bypass all permission checks. Locked-out accounts are denied everything.
Sessions are tracked server-side in the database, validated on every request.

## Quick Start

```bash
git clone https://github.com/jamswat/streetsign.git
cd streetsign
./setup.sh
./run.py
```

Open http://localhost:5000 — default login is `admin` / `password`.
**Change the password immediately** before deploying.

## Docker

A multi-stage Docker image is provided — the build compiles C extensions in a
builder stage and ships a slim final image (~45 MB) that runs as a non-root
`streetsign` user. Static assets are served efficiently in-process by
[WhiteNoise](https://whitenoise.evans.io/) (no nginx sidecar required), so the
container can be exposed directly or placed behind any reverse proxy.

### Quick start

```bash
docker build -t streetsign .
docker run -d --name streetsign -p 5000:5000 streetsign
```

Open http://localhost:5000 — default login is `admin` / `password`.

### docker-compose

```bash
docker compose up -d
```

This brings up a single `app` service on `${WEB_PORT:-5000}`. Two named volumes
are created automatically and persist across rebuilds:

| Volume      | Mount path                                    | Purpose                          |
|-------------|-----------------------------------------------|----------------------------------|
| `db_data`   | `/data`                                       | SQLite database                  |
| `uploads`   | `/app/streetsign_server/static/user_files`    | User-uploaded images, fonts, etc.|

Built-in static assets (`main.js`, `style.css`, `lib/`, `screens/`) are baked
into the image and are **not** mounted on a volume, so changes to them appear
on the next rebuild without stale-file masking. Only `user_files/` (runtime
uploads) is persisted.

### Persistent data (plain `docker run`)

Mount volumes for the SQLite database and uploaded files, otherwise data is
lost when the container is removed:

```bash
docker run -d -p 5000:5000 \
  -v streetsign-db:/data \
  -v streetsign-uploads:/app/streetsign_server/static/user_files \
  streetsign
```

On first start (empty `/data`), the container seeds a fresh database with the
default admin user, feeds, and a sample screen. On subsequent starts it only
runs pending migrations.

### Configuration

| Variable         | Default                | Notes                                            |
|------------------|------------------------|--------------------------------------------------|
| `SECRET_KEY`     | `change-me`            | Flask session-signing key. The entrypoint refuses to start with the default. Generate with `python3 -c "import uuid; print(uuid.uuid4())"` and pass via `-e SECRET_KEY=...` or a `.env` file. |
| `WEB_PORT`       | `5000`                 | Host port to publish (compose only)              |
| `PORT`           | `5000`                 | Port the server listens on inside the container  |
| `HOST`           | `0.0.0.0`              | Bind address inside the container                |
| `DATABASE_FILE`  | `/data/database.db`    | SQLite path (already volume-mounted in image)   |

Override at runtime, e.g. to serve on port 8080:

```bash
docker run -d -p 8080:8080 -e PORT=8080 streetsign
```

Or with compose, publish on a different host port:

```bash
WEB_PORT=8080 docker compose up -d
```

For production you should mount your own `config.py` (see `config_default.py`
for the full list of options):

```bash
docker run -d -p 5000:5000 -v "$PWD/config.py:/app/config.py:ro" streetsign
```

### Reverse proxy

For internet-facing deployments, run the container behind a reverse proxy that
terminates TLS (Caddy, Traefik, Nginx Proxy Manager, host nginx, Cloudflare
Tunnel, etc.). Point the proxy at the container's `:5000` and let it handle
HTTPS, gzip, and large-upload timeouts — there is no need for a separate nginx
container in the compose stack.

## Production

```bash
./run.py waitress
```

## Upgrading

1. Backup `database.db` and `config.py`
2. `git pull`
3. `make migrate`
4. Restart the server

## Requirements

- Python 3.9+
- ImageMagick (for image resizing and thumbnails)

Debian/Ubuntu:

```bash
apt-get install python3-dev python3-pip imagemagick
```

The `setup.sh` script creates a `.virtualenv` with all Python dependencies.
To use the virtualenv directly: `.virtualenv/bin/python`.

## Development

```bash
.virtualenv/bin/python -m pytest tests/
.virtualenv/bin/python -m pylint streetsign_server/
```

There is a pre-commit hook in `.setup/hooks/` that runs pylint before commits.
Skip it with `git commit --no-verify`.

## Documentation

Full documentation at [streetsign.readthedocs.org](http://streetsign.readthedocs.org/en/latest/)

## Troubleshooting

**Why isn't my post showing up?**
- Is it published?
- Does the screen have the correct feeds selected?
- Are time restrictions blocking it?
- Is it within its active lifetime (start/end dates)?

## Changelog

See the [CHANGELOG](CHANGELOG.md) for a summary of improvements.

## Credits

StreetSign was created by **Daniel Fairhead** for Teenstreet 2013. It is made
available under the GPLv3 with his permission. The original source was hosted on
Bitbucket.

## AI Usage

Code in this repository has been developed with assistance from AI coding tools,
including the Bootstrap 3→5 migration, Knockout.js→Alpine.js replacement,
HTML/CSS/JS modernization, and dependency updates.

## License

[GPLv3](COPYING)
