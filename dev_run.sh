#!/usr/bin/env bash
#
# Run a throwaway StreetSign development server.
#
#   ./dev_run.sh            start the dev server on 127.0.0.1:5000
#   ./dev_run.sh reset      wipe the dev database and start fresh
#   ./dev_run.sh seed       create/seed the dev database, then exit
#   ./dev_run.sh clean      remove all generated dev files (.dev/)
#   ./dev_run.sh help       show this help
#
# Everything this script generates lives in .dev/ (git-ignored), so it never
# touches the database.db / config.py used by `make all`. Override the listen
# address with HOST=... PORT=... and enable auto-reload with FLASK_DEBUG=1.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY="$ROOT/.venv/bin/python3"
DEV_DIR="$ROOT/.dev"
DEV_DB="$DEV_DIR/database.db"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5000}"

log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
    sed -n '3,13p' "$0" | sed 's/^# \{0,1\}//'
}

ensure_venv() {
    if [ ! -x "$PY" ]; then
        log "No .venv found; creating one with 'uv sync --extra dev'..."
        command -v uv >/dev/null 2>&1 || die \
            "uv is required to create .venv (see README 'Requirements')."
        uv sync --extra dev
    fi
}

seed_db() {
    ensure_venv
    mkdir -p "$DEV_DIR"

    if [ -f "$DEV_DB" ]; then
        log "Using existing dev database: $DEV_DB"
    else
        log "Seeding a fresh dev database: $DEV_DB"
    fi

    # db.make() creates the tables and seeds demo users/screen; it is safe to
    # re-run. DATABASE_FILE is read from the environment by config_default.py.
    DATABASE_FILE="$DEV_DB" "$PY" -c 'import db; db.make()'
}

run_server() {
    seed_db
    log "Starting dev server: http://$HOST:$PORT  (login: admin / admin)"
    log "Generated files: $DEV_DIR  —  clean up later with ./dev_run.sh clean"
    log "Press Ctrl-C to stop."
    DATABASE_FILE="$DEV_DB" HOST="$HOST" PORT="$PORT" exec "$PY" run.py
}

clean() {
    if [ -e "$DEV_DIR" ]; then
        log "Removing generated dev files: $DEV_DIR"
        rm -rf "$DEV_DIR"
    else
        log "Nothing to clean."
    fi
}

case "${1:-run}" in
    run|"")    run_server ;;
    reset)     clean; run_server ;;
    seed)      seed_db ;;
    clean)     clean ;;
    -h|--help|help|usage) usage ;;
    *)         warn "Unknown command: $1"; usage; exit 2 ;;
esac