# StreetSign

A lightweight digital signage server written in Python by **Daniel Fairhead**.
Originally created for [Teenstreet 2013](http://www.teenstreet.de) in Germany,
it has been used at large conferences and in corporate environments since.

Built with Flask, Peewee, Alpine.js, and SQLite — manage content feeds, schedule
posts, and display them on configurable screen layouts with smooth fade and scroll
transitions.

---

## Features

- **Content types** — plain text, rich text (HTML), images, video, external
  webpages, web hooks, and raw HTML. Plugin system for adding more.
- **Screen layouts** — multi-zone displays with configurable backgrounds, CSS,
  fonts, scroll/fade transitions, and aspect ratio override.
- **Scheduling** — per-post start/end lifetimes, time-of-day restrictions,
  configurable display duration.
- **Permissions** — user and group-based read/write/publish permissions per feed.
- **External data** — import posts automatically from RSS/Atom feeds or local
  image folders.
- **Client aliases** — route different display clients to different screens.
- **Magic variables** — `%%TIME%%` and `%%DATE%%` in posts update live on screen.

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
builder stage and ships a slim final image (~80 MB) that runs as a non-root
`streetsign` user.

```bash
docker build -t streetsign .
docker run -d --name streetsign -p 5000:5000 streetsign
```

Open http://localhost:5000 — default login is `admin` / `password`.

### Persistent data

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
| `PORT`           | `5000`                 | HTTP port the server listens on                  |
| `HOST`           | `0.0.0.0`              | Bind address                                     |
| `DATABASE_FILE`  | `/data/database.db`    | SQLite path (already volume-mounted in image)    |

Override at runtime, e.g. to serve on port 8080:

```bash
docker run -d -p 8080:8080 -e PORT=8080 streetsign
```

> The Flask `SECRET_KEY` is generated at **build** time by
> `.setup/make_initial_config_file.py` and baked into the image. For production
> you should mount your own `config.py` (see `config_default.py` for the full
> list of options) rather than rely on the build-time key:
>
> ```bash
> docker run -d -p 5000:5000 -v "$PWD/config.py:/app/config.py:ro" streetsign
> ```

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
.virtualenv/bin/python -m pytest tests/          # 158 tests
.virtualenv/bin/python -m pylint streetsign_server/  # lint
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
