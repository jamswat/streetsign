'''
    Tests for the connected-clients registry, heartbeat, and force-refresh
    command channel (admin "Connected Clients" page).
'''

# pylint: disable=import-error,too-many-public-methods,too-few-public-methods
# pylint: disable=missing-docstring,protected-access

import sys
import os
import unittest
from datetime import datetime, timedelta, timezone
from flask import Flask, json, jsonify, request

sys.path.append(os.path.dirname(__file__) + '/..')

import streetsign_server.models as models
from streetsign_server import apply_proxy_fix
from streetsign_server.logic import clients as clients_logic
from streetsign_server.models import now

from unittest_helpers import StreetSignTestCase


ADMIN = 'admin'
ADMINPASS = 'adminpass'
USER = 'user'
USERPASS = 'userpass'


class ClientTestBase(StreetSignTestCase):
    ''' Shared fixtures: a screen, an admin and a normal user. '''

    def setUp(self):
        super().setUp()
        clients_logic.reset()

        self.screen = models.Screen(urlname='TestScreen')
        self.screen.save()

        self.admin = models.User(displayname='Admin', loginname=ADMIN,
                                 emailaddress='admin@example.com',
                                 passwordhash='', is_admin=True)
        self.admin.set_password(ADMINPASS)
        self.admin.save()

        self.user = models.User(displayname='User', loginname=USER,
                                emailaddress='user@example.com',
                                passwordhash='', is_admin=False)
        self.user.set_password(USERPASS)
        self.user.save()

    def tearDown(self):
        clients_logic.reset()
        super().tearDown()


class TestHeartbeat(ClientTestBase):
    ''' The public heartbeat endpoint. '''

    def test_heartbeat_public(self):
        resp = self.client.get(f'/screens/heartbeat/{self.screen.id}')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('refresh', data)
        self.assertIn('server', data)
        self.assertEqual(data['interval'], 10)

    def test_heartbeat_no_store(self):
        resp = self.client.get(f'/screens/heartbeat/{self.screen.id}')
        self.assertIn('no-store', resp.headers.get('Cache-Control', ''))

    def test_heartbeat_registers_client(self):
        self.client.get(f'/screens/heartbeat/{self.screen.id}?alias=mainhall')

        connected = clients_logic.connected_clients()
        self.assertEqual(len(connected), 1)
        self.assertEqual(connected[0]['alias'], 'mainhall')
        self.assertEqual(connected[0]['screen'], 'TestScreen')
        self.assertEqual(connected[0]['ip'], '127.0.0.1')

    def test_heartbeat_unknown_screen_still_records(self):
        self.client.get('/screens/heartbeat/99999?alias=ghost')

        connected = clients_logic.connected_clients()
        self.assertEqual(len(connected), 1)
        self.assertEqual(connected[0]['alias'], 'ghost')
        self.assertIsNone(connected[0]['screen'])

    def test_forwarded_header_ignored_without_proxy_config(self):
        # TRUSTED_PROXY_HOPS defaults to 0, so a client-supplied
        # X-Forwarded-For must not influence the recorded address.
        self.client.get(
            f'/screens/heartbeat/{self.screen.id}',
            headers={'X-Forwarded-For': '203.0.113.5'})

        connected = clients_logic.connected_clients()
        self.assertEqual(connected[0]['ip'], '127.0.0.1')

    def test_proxy_resolved_remote_addr_is_recorded(self):
        # ProxyFix rewrites REMOTE_ADDR from X-Forwarded-For; client_ip()
        # records whatever the WSGI environ reports.
        self.client.get(
            f'/screens/heartbeat/{self.screen.id}',
            environ_overrides={'REMOTE_ADDR': '203.0.113.5'})

        connected = clients_logic.connected_clients()
        self.assertEqual(connected[0]['ip'], '203.0.113.5')

    def test_oversized_fields_are_truncated(self):
        self.client.get(
            f'/screens/heartbeat/{self.screen.id}',
            query_string={'alias': 'A' * 500},
            headers={'User-Agent': 'U' * 1000})

        connected = clients_logic.connected_clients()
        self.assertEqual(len(connected[0]['alias']), 200)
        self.assertEqual(len(connected[0]['user_agent']), 300)

    def test_stale_client_expires(self):
        self.client.get(f'/screens/heartbeat/{self.screen.id}')
        # Age the entry beyond the TTL.
        key = next(iter(clients_logic._presence))
        clients_logic._presence[key]['last_seen'] = now() - timedelta(seconds=120)

        self.assertEqual(clients_logic.connected_clients(), [])

    def test_last_seen_is_timezone_aware(self):
        # The browser parses the ISO string; without an offset it assumes
        # browser-local time and renders a constant, timezone-sized age
        # (e.g. "60m ago" in a UTC container viewed from UTC+1).
        self.client.get(f'/screens/heartbeat/{self.screen.id}')

        stamp = clients_logic.connected_clients()[0]['last_seen']
        parsed = datetime.fromisoformat(stamp)
        self.assertIsNotNone(parsed.tzinfo)
        age = abs((datetime.now(timezone.utc) - parsed).total_seconds())
        self.assertLess(age, 5)


class TestClientsPage(ClientTestBase):
    ''' The admin-only connected clients page and JSON endpoint. '''

    def test_page_requires_login(self):
        resp = self.client.get('/clients')
        self.assertEqual(resp.status_code, 403)

    def test_page_forbidden_for_non_admin(self):
        self.login(USER, USERPASS)
        resp = self.client.get('/clients')
        self.assertEqual(resp.status_code, 403)

    def test_page_allowed_for_admin(self):
        self.client.get(f'/screens/heartbeat/{self.screen.id}?alias=mainhall')
        self.login(ADMIN, ADMINPASS)
        resp = self.client.get('/clients')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Connected Clients', resp.data)
        self.assertIn(b'mainhall', resp.data)
        self.assertIn(b'127.0.0.1', resp.data)

    def test_json_forbidden_for_non_admin(self):
        self.login(USER, USERPASS)
        resp = self.client.get('/clients/json')
        self.assertEqual(resp.status_code, 403)

    def test_json_allowed_for_admin(self):
        self.client.get(f'/screens/heartbeat/{self.screen.id}?alias=mainhall')
        self.login(ADMIN, ADMINPASS)
        resp = self.client.get('/clients/json')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['clients']), 1)
        self.assertEqual(data['clients'][0]['alias'], 'mainhall')


class TestRefresh(ClientTestBase):
    ''' Forcing clients to reload. '''

    def _heartbeat_refresh(self):
        resp = self.client.get(f'/screens/heartbeat/{self.screen.id}')
        return json.loads(resp.data)['refresh']

    def test_refresh_requires_admin(self):
        self.login(USER, USERPASS)
        resp = self.client.post('/clients/refresh', data={'target': 'all'})
        self.assertEqual(resp.status_code, 403)

    def test_refresh_all_changes_heartbeat(self):
        self.login(ADMIN, ADMINPASS)
        before = self._heartbeat_refresh()

        resp = self.client.post('/clients/refresh', data={'target': 'all'})
        self.assertEqual(resp.status_code, 200)

        after = self._heartbeat_refresh()
        self.assertEqual(after, before + 1)

    def test_refresh_specific_alias(self):
        self.login(ADMIN, ADMINPASS)
        before = self._heartbeat_refresh()

        resp = self.client.post('/clients/refresh',
                                data={'target': 'alias:mainhall'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._heartbeat_refresh(), before)

        # A client showing that alias sees the change.
        resp = self.client.get(
            f'/screens/heartbeat/{self.screen.id}?alias=mainhall')
        self.assertEqual(json.loads(resp.data)['refresh'], before + 1)

    def test_refresh_invalid_target(self):
        self.login(ADMIN, ADMINPASS)
        resp = self.client.post('/clients/refresh',
                                data={'target': 'bogus'})
        self.assertEqual(resp.status_code, 400)


class TestApplyProxyFix(unittest.TestCase):
    ''' apply_proxy_fix wires Werkzeug's ProxyFix from a hop count. '''

    @staticmethod
    def _make_app():
        flask_app = Flask(__name__)

        @flask_app.route('/whoami')
        def whoami():
            return jsonify(remote_addr=request.remote_addr,
                           scheme=request.scheme)

        return flask_app

    def _get_whoami(self, hops, headers):
        flask_app = self._make_app()
        flask_app.wsgi_app = apply_proxy_fix(flask_app.wsgi_app, hops)
        resp = flask_app.test_client().get('/whoami', headers=headers)
        return json.loads(resp.data)

    def test_zero_hops_ignores_forwarded_headers(self):
        data = self._get_whoami(0, {'X-Forwarded-For': '203.0.113.5',
                                    'X-Forwarded-Proto': 'https'})
        self.assertEqual(data['remote_addr'], '127.0.0.1')
        self.assertEqual(data['scheme'], 'http')

    def test_non_numeric_hops_ignored(self):
        data = self._get_whoami('nonsense',
                                {'X-Forwarded-For': '203.0.113.5'})
        self.assertEqual(data['remote_addr'], '127.0.0.1')

    def test_one_hop_trusts_forwarded_headers(self):
        data = self._get_whoami(1, {'X-Forwarded-For': '203.0.113.5',
                                    'X-Forwarded-Proto': 'https'})
        self.assertEqual(data['remote_addr'], '203.0.113.5')
        self.assertEqual(data['scheme'], 'https')

    def test_two_hops_uses_second_from_right(self):
        data = self._get_whoami(2, {'X-Forwarded-For': '203.0.113.5, 10.0.0.1'})
        self.assertEqual(data['remote_addr'], '203.0.113.5')

    def test_too_few_forwarded_values_ignored(self):
        data = self._get_whoami(2, {'X-Forwarded-For': '203.0.113.5'})
        self.assertEqual(data['remote_addr'], '127.0.0.1')


if __name__ == '__main__':
    unittest.main()
