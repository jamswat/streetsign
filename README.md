# StreetSign

A lightweight digital signage server written in Python by **Daniel Fairhead**.
Originally created for [Teenstreet 2013](http://www.teenstreet.de) in Germany,
it has been used at large conferences and in corporate environments since.

Built with Flask, Peewee, and SQLite — manage content feeds, schedule posts, and
display them on configurable screen layouts with smooth fade and scroll
transitions.

---

## Features

- **Content types** — plain text, rich text (HTML), advanced documents, images,
  external webpages, web hooks, and raw HTML. Plugin system for adding more.
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

```bash
docker build -t streetsign .
docker run -p 5000:5000 streetsign
```

## Production

```bash
./run.py waitress
```

For larger deployments, put nginx or a similar reverse proxy in front of the
WSGI server and serve the `static/` directory directly.

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

## Credits

StreetSign was created by **Daniel Fairhead** for Teenstreet 2013. It is made
available under the GPLv3 with his permission. The original source was hosted on
Bitbucket.

## AI Usage

Code in this repository has been developed with assistance from AI coding tools,
including the Bootstrap 3→5 migration, dependency updates, Python 3 fixes, bug
fixes, CSRF protection, and the raw HTML post type.

## License

[GPLv3](COPYING)
