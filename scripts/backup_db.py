#!/usr/bin/env python3
'''
    Backup the StreetSign SQLite database safely.

    A naïve ``cp database.db`` misses the WAL file (database.db-wal) and
    can produce a corrupt snapshot if a write is in flight.  This script
    uses the SQLite online backup API (available in Python's sqlite3
    module as ``backup()``), which produces a consistent copy while the
    server keeps running.

    Usage::

        .venv/bin/python scripts/backup_db.py                 # writes to <database>.bak
        .venv/bin/python scripts/backup_db.py /path/to/backup.db
        DATABASE_FILE=/data/database.db .venv/bin/python scripts/backup_db.py

    In Docker / cron, mount a backup volume and run::

        docker exec streetsign python scripts/backup_db.py /backups/streetsign-$(date +%F).db
'''

import os
import sys
import sqlite3
import logging

logger = logging.getLogger('streetsign.backup')


def get_db_path():
    ''' Resolve the database path the same way the app does. '''
    # Allow explicit argument.
    if len(sys.argv) > 1:
        return sys.argv[1]
    # Then env var ( honoured by config_default.py ).
    path = os.environ.get('DATABASE_FILE')
    if path:
        return path
    # Fall back to importing the app config.
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        import streetsign_server  # noqa: F401
        return streetsign_server.app.config['DATABASE_FILE']
    except Exception:  # pylint: disable=broad-except
        return 'database.db'


def backup(src, dst):
    ''' Copy the live SQLite database at *src* to *dst* using the online
        backup API so the WAL is merged and writes can continue. '''
    if src != ':memory:' and not os.path.exists(src):
        logger.error('source database does not exist: %s', src)
        sys.exit(1)

    if os.path.dirname(dst):
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)

    src_conn = sqlite3.connect(src)
    dst_conn = sqlite3.connect(dst)

    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    logger.info('backup complete: %s -> %s', src, dst)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    src = get_db_path()
    dst = (sys.argv[1] if len(sys.argv) > 1
           else src + '.bak')

    logger.info('starting backup: %s -> %s', src, dst)
    backup(src, dst)


if __name__ == '__main__':
    main()
