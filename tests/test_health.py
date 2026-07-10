''' Tests for the /health liveness endpoint. '''

#pylint: disable=import-error,too-many-public-methods,too-few-public-methods,missing-docstring

import sys
import os
from flask import json

sys.path.append(os.path.dirname(__file__) + '/..')

from unittest_helpers import StreetSignTestCase


class TestHealth(StreetSignTestCase):
    ''' The /health endpoint should return 200 with status ok when the
        database is reachable. '''

    def test_health_ok(self):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['database'], 'ok')

    def test_health_no_auth_required(self):
        ''' /health must be accessible without logging in. '''
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    import unittest
    unittest.main()
