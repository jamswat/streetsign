'''
    Tests for the connected-clients registry, heartbeat, and force-refresh
    command channel (admin "Connected Clients" page).
'''

# pylint: disable=import-error,too-many-public-methods,too-few-public-methods
# pylint: disable=missing-docstring,protected-access

import sys
import os
from datetime import datetime, timedelta, timezone
from flask import json

sys.path.append(os.path.dirname(__file__) + '/..')

import streetsign_server.models as models
from streetsign_server import app
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

    def test_x_forwarded_for_uses_leftmost_hop(self):
        # Behind several proxies each appends to the right, so the left-most
        # entry is the originating client.
        self.client.get(
            f'/screens/heartbeat/{self.screen.id}',
            headers={'X-Forwarded-For': '203.0.113.5, 10.0.0.1'})

        connected = clients_logic.connected_clients()
        self.assertEqual(connected[0]['ip'], '203.0.113.5')

    def test_x_forwarded_for_single_entry(self):
        self.client.get(
            f'/screens/heartbeat/{self.screen.id}',
            headers={'X-Forwarded-For': '203.0.113.9'})

        connected = clients_logic.connected_clients()
        self.assertEqual(connected[0]['ip'], '203.0.113.9')

    def test_x_forwarded_for_invalid_falls_back_to_peer(self):
        self.client.get(
            f'/screens/heartbeat/{self.screen.id}',
            headers={'X-Forwarded-For': 'not-an-ip'})

        connected = clients_logic.connected_clients()
        self.assertEqual(connected[0]['ip'], '127.0.0.1')

    def test_oversized_fields_are_truncated(self):
        self.client.get(
            f'/screens/heartbeat/{self.screen.id}',
            query_string={'alias': 'A' * 500},
            headers={'User-Agent': 'U' * 1000})

        connected = clients_logic.connected_clients()
        self.assertEqual(len(connected[0]['alias']), 200)
        self.assertEqual(len(connected[0]['user_agent']), 300)

    def test_x_forwarded_for_ignored_when_disabled(self):
        old = app.config.get('TRUST_PROXY_HEADERS')
        app.config['TRUST_PROXY_HEADERS'] = False
        try:
            self.client.get(
                f'/screens/heartbeat/{self.screen.id}',
                headers={'X-Forwarded-For': '203.0.113.5'})
            connected = clients_logic.connected_clients()
            self.assertEqual(connected[0]['ip'], '127.0.0.1')
        finally:
            app.config['TRUST_PROXY_HEADERS'] = old

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


if __name__ == '__main__':
    import unittest
    unittest.main()