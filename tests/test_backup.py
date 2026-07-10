''' Tests for the database backup script. '''

#pylint: disable=import-error,too-many-public-methods,too-few-public-methods,missing-docstring

import sys
import os
import sqlite3
import tempfile
import importlib
import unittest

sys.path.append(os.path.dirname(__file__) + '/..')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

_backup = importlib.import_module('backup_db')


class TestBackup(unittest.TestCase):
    ''' The backup function must produce a consistent, queryable copy of the
        source database, including data written before the backup. '''

    def setUp(self):
        self.src = tempfile.mktemp(suffix='.db')
        self.dst = tempfile.mktemp(suffix='.bak')
        conn = sqlite3.connect(self.src)
        conn.execute('CREATE TABLE foo (id INTEGER, name TEXT)')
        conn.execute("INSERT INTO foo VALUES (1, 'hello')")
        conn.execute("INSERT INTO foo VALUES (2, 'world')")
        conn.execute('PRAGMA journal_mode=wal')
        conn.commit()
        conn.close()

    def tearDown(self):
        for p in (self.src, self.dst, self.src + '-wal', self.src + '-shm',
                  self.dst + '-wal', self.dst + '-shm'):
            if os.path.exists(p):
                os.unlink(p)

    def test_backup_contains_all_data(self):
        _backup.backup(self.src, self.dst)
        self.assertTrue(os.path.exists(self.dst))

        conn = sqlite3.connect(self.dst)
        rows = conn.execute('SELECT * FROM foo ORDER BY id').fetchall()
        conn.close()

        self.assertEqual(rows, [(1, 'hello'), (2, 'world')])

    def test_backup_destination_dir_created(self):
        dst = os.path.join(tempfile.mkdtemp(), 'sub', 'backup.db')
        _backup.backup(self.src, dst)
        self.assertTrue(os.path.exists(dst))
        os.unlink(dst)
        os.rmdir(os.path.dirname(dst))
        os.rmdir(os.path.dirname(os.path.dirname(dst)))

    def test_backup_nonexistent_source(self):
        with self.assertRaises(SystemExit):
            _backup.backup('/no/such/file.db', self.dst)


if __name__ == '__main__':
    unittest.main()
