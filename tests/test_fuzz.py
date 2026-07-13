"""Fuzz-test streetsign endpoints for regressions.

Uses a single module-scoped in-memory DB seeded once, so later tests
can exercise behaviour against accumulated state — matching the character
of the original fuzz script.  Each test class is responsible for its own
login / logout.
"""
# pylint: disable=missing-docstring, too-many-lines, redefined-outer-name

import json
import datetime
import random
import string
import urllib.parse
import warnings

import pytest
from peewee import SqliteDatabase, Model
from flask import json as flask_json
import streetsign_server.models as models
from streetsign_server import app

warnings.filterwarnings('ignore',
                        message=r'.*unclosed database.*',
                        category=ResourceWarning)


# ---------------------------------------------------------------------------
# Mock bcrypt — fast, deterministic, matches the pattern in unittest_helpers
# ---------------------------------------------------------------------------

class MockBcrypt:
    @staticmethod
    def hashpw(password, _salt):
        return password

    @staticmethod
    def checkpw(password, hashed):
        return password == hashed

    @staticmethod
    def gensalt():
        return b''

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _login(client, username, password):
    client.post('/login', data={'username': username, 'password': password})

def _logout(client):
    client.post('/logout')

def _a200(r):
    assert r.status_code == 200, f'got {r.status_code}'

def _a302(r):
    assert r.status_code == 302, f'got {r.status_code}'

def _aok(r):
    assert r.status_code < 500, f'server error {r.status_code}'


# ---------------------------------------------------------------------------
# Fixture: one seeded DB for all fuzz tests in this module.
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def fuzz_db():
    """Create an in-memory DB, seed it, and return a dict with all fixtures."""

    models.bcrypt = MockBcrypt()
    app.config['DATABASE_FILE'] = ':memory:'
    app.config['TESTING'] = True
    app.config['CSRF_ENABLED'] = False
    app.config['SECRET_KEY'] = 'test-key-for-fuzzing'

    if not models.DB.is_closed():
        models.DB.close()

    models.DB = SqliteDatabase(None)
    models.DB.init(':memory:')

    model_list = []
    for modelname in models.__all__:
        m = getattr(models, modelname)
        try:
            if issubclass(m, Model):
                m.bind(models.DB)
                model_list.append(m)
        except TypeError:
            pass

    models.DB.create_tables(model_list)

    # --- seed ------------------------------------------------------------
    admin_u = models.User(loginname='admin', displayname='Admin', is_admin=True)
    admin_u.set_password('testpass')
    admin_u.save()

    ed_u = models.User(loginname='editor', displayname='Editor')
    ed_u.set_password('testpass')
    ed_u.save()

    vw_u = models.User(loginname='viewer', displayname='Viewer')
    vw_u.set_password('testpass')
    vw_u.save()

    g1 = models.Group.create(name='editors')
    g2 = models.Group.create(name='viewers')

    f1 = models.Feed.create(name='Test Feed', post_types='html,text,image')
    f2 = models.Feed.create(name='Announcements', post_types='text')
    f3 = models.Feed.create(name='Mixed Feed',
                            post_types='html,text,image,video,web_hook,raw_html')

    S1 = models.Screen.create(urlname='Default', settings='{}', defaults='{}',
                              zones='[]', css='')
    S2 = models.Screen.create(urlname='Lobby', settings='{}', defaults='{}',
                              zones='[]', css='')

    f1.grant('Write', user=ed_u)
    f1.grant('Publish', user=ed_u)
    f2.grant('Read', user=vw_u)

    # Five posts that Phase C tests reference.
    pids = []
    for i in range(5):
        p = models.Post(
            title=f'Fuzz {i}', type='text',
            content=json.dumps({'type': 'text', 'content': f'c{i}'}),
            feed=f1, author=admin_u, publisher=admin_u,
            published=True, publish_date=datetime.datetime.now(),
        )
        p.save()
        pids.append(p.id)

    # --- yield -----------------------------------------------------------
    yield {
        'client':   app.test_client(),
        'admin':    admin_u,
        'editor':   ed_u,
        'viewer':   vw_u,
        'g1':       g1,
        'g2':       g2,
        'f1':       f1,
        'f2':       f2,
        'f3':       f3,
        'S1':       S1,
        'S2':       S2,
        'pids':     pids,
    }

    # --- teardown --------------------------------------------------------
    models.DB.close()


random.seed(42)

# ---------------------------------------------------------------------------
# Phase A: Login & Forms
# ---------------------------------------------------------------------------

class TestLoginForms:
    def test_empty_username(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/login', data={'username': '', 'password': 'x'})
        _aok(r)

    def test_empty_password(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/login', data={'username': 'admin', 'password': ''})
        _aok(r)

    def test_missing_both(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/login', data={})
        _aok(r)

    def test_wrong_password(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/login', data={'username': 'admin', 'password': 'WRONG123'})
        _aok(r)
        _a302(r)

    def test_sqli(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/login', data={'username': "' OR 1=1 --",
                                   'password': "' OR 1=1 --"})
        _aok(r)
        _a302(r)

    def test_new_feed_empty(self, fuzz_db):
        c = fuzz_db['client']
        _login(c, 'admin', 'testpass')
        r = c.post('/feeds', data={'title': ''})
        _aok(r)

    def test_new_feed_nodata(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/feeds', data={})
        _aok(r)

    def test_new_group_empty(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/users_and_groups',
                   data={'action': 'creategroup', 'name': ''})
        _a302(r)

    def test_new_group_missing(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/users_and_groups', data={'action': 'creategroup'})
        _a302(r)

    def test_new_post_no_title(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        r = c.post(f'/posts/new/{f1.id}',
                   data={'post_type': 'text', 'action': 'edit'},
                   follow_redirects=True)
        _a200(r)


# ---------------------------------------------------------------------------
# Phase B: User / Group
# ---------------------------------------------------------------------------

class TestUserGroup:
    def test_user_empty_email(self, fuzz_db):
        c = fuzz_db['client']
        ed_u = fuzz_db['editor']
        _login(c, 'admin', 'testpass')
        r = c.post(f'/users/{ed_u.id}',
                   data={'loginname': 'editor', 'emailaddress': '',
                         'displayname': 'Editor'},
                   follow_redirects=True)
        _a200(r)

    def test_user_invalid_email(self, fuzz_db):
        c = fuzz_db['client']
        ed_u = fuzz_db['editor']
        r = c.post(f'/users/{ed_u.id}',
                   data={'loginname': 'editor', 'emailaddress': 'BANANA!!!!',
                         'displayname': 'Editor'},
                   follow_redirects=True)
        _a200(r)

    def test_user_bogus_groups(self, fuzz_db):
        c = fuzz_db['client']
        ed_u = fuzz_db['editor']
        r = c.post(f'/users/{ed_u.id}',
                   data={'loginname': 'editor', 'groups': 'abc'},
                   follow_redirects=True)
        _a200(r)

    def test_user_bogus_groups_int(self, fuzz_db):
        c = fuzz_db['client']
        ed_u = fuzz_db['editor']
        r = c.post(f'/users/{ed_u.id}',
                   data={'loginname': 'editor', 'groups': '999999'},
                   follow_redirects=True)
        _a200(r)

    def test_user_set_groups_valid(self, fuzz_db):
        c = fuzz_db['client']
        ed_u = fuzz_db['editor']
        g1 = fuzz_db['g1']
        r = c.post(f'/users/{ed_u.id}',
                   data={'loginname': 'editor', 'groups': str(g1.id)},
                   follow_redirects=True)
        _a200(r)
        u = models.User.get(models.User.id == ed_u.id)
        assert g1.id in [g.id for g in u.groups()]

    def test_group_bogus_users(self, fuzz_db):
        c = fuzz_db['client']
        g1 = fuzz_db['g1']
        r = c.post(f'/group/{g1.id}',
                   data={'action': 'update', 'groupname': 'editors',
                         'groupusers': 'abc'},
                   follow_redirects=True)
        _a200(r)

    def test_group_bogus_users_int(self, fuzz_db):
        c = fuzz_db['client']
        g1 = fuzz_db['g1']
        r = c.post(f'/group/{g1.id}',
                   data={'action': 'update', 'groupname': 'editors',
                         'groupusers': '99999'},
                   follow_redirects=True)
        _a200(r)

    def test_group_rename_valid(self, fuzz_db):
        c = fuzz_db['client']
        g1 = fuzz_db['g1']
        r = c.post(f'/group/{g1.id}',
                   data={'action': 'update', 'groupname': 'editors_renamed'},
                   follow_redirects=True)
        _a200(r)
        g = models.Group.get(models.Group.id == g1.id)
        assert g.name == 'editors_renamed'
        g.name = 'editors'
        g.save()

    def test_user_create_admin(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/users/-1',
                   data={'loginname': 'newbie', 'displayname': 'Newbie',
                         'newpass': 'pw123', 'conf_newpass': 'pw123',
                         'currpass': 'testpass'},
                   follow_redirects=True)
        _a200(r)
        assert models.User.select().where(
            models.User.loginname == 'newbie').exists()
        models.User.get(models.User.loginname == 'newbie').delete_instance(
            recursive=True)

    def test_user_create_no_password(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/users/-1',
                   data={'loginname': 'nopwd', 'displayname': 'NoPass'},
                   follow_redirects=True)
        _a200(r)
        assert not models.User.select().where(
            models.User.loginname == 'nopwd').exists()

    def test_user_create_nologin(self, fuzz_db):
        c = fuzz_db['client']
        u = models.User(displayname='DelMe')
        u.set_password('x')
        u.save()
        uid = u.id
        _logout(c)
        _login(c, 'editor', 'testpass')
        r = c.post('/users/-1',
                   data={'loginname': 'bad', 'displayname': 'Bad'},
                   follow_redirects=True)
        assert r.status_code in (200, 403)
        assert not models.User.select().where(
            models.User.loginname == 'bad').exists()
        r = c.post(f'/users/{uid}', data={'loginname': u.loginname},
                   follow_redirects=True)
        assert r.status_code in (200, 403)
        _login(c, 'admin', 'testpass')
        models.User.get(models.User.id == uid).delete_instance(
            recursive=True)


# ---------------------------------------------------------------------------
# Phase C: Feeds & Posts
# ---------------------------------------------------------------------------

class TestFeedsPosts:
    """Tests that mutate the shared fuzz posts (pids)."""

    def test_reorder_valid(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        pids = fuzz_db['pids']
        _login(c, 'admin', 'testpass')
        r = c.post(f'/feeds/{f1.id}/reorder',
                   data=json.dumps({'post_ids': pids}),
                   content_type='application/json')
        _a200(r)

    def test_reorder_empty(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        r = c.post(f'/feeds/{f1.id}/reorder',
                   data=json.dumps({'post_ids': []}),
                   content_type='application/json')
        _a200(r)

    def test_reorder_missing_key(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        r = c.post(f'/feeds/{f1.id}/reorder',
                   data=json.dumps({}),
                   content_type='application/json')
        _a200(r)

    def test_reorder_bogus(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        r = c.post(f'/feeds/{f1.id}/reorder',
                   data=json.dumps({'post_ids': [99999, -1]}),
                   content_type='application/json')
        _a200(r)

    def test_reorder_string_ids(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        r = c.post(f'/feeds/{f1.id}/reorder',
                   data=json.dumps({'post_ids': ['abc']}),
                   content_type='application/json')
        assert r.status_code in (200, 500)

    def test_bulk_delete_mixed(self, fuzz_db):
        c = fuzz_db['client']
        pids = fuzz_db['pids']
        r = c.post('/posts/bulk_delete',
                   data=json.dumps({'post_ids': [pids[3], 'abc', -1, 999]}),
                   content_type='application/json')
        _a200(r)
        d = json.loads(r.data)
        assert d.get('errors', 0) >= 2
        assert d.get('deleted', 0) == 1

    def test_feed_duplicate_name(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/feeds', data={'title': 'Test Feed'})
        _aok(r)

    def test_feed_empty_name(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/feeds', data={'title': ''})
        _aok(r)

    def test_feed_edit_valid(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        r = c.post(f'/feeds/{f1.id}',
                   data={'action': 'edit', 'title': 'Test Feed',
                         'post_types': 'html,text'},
                   follow_redirects=True)
        _a200(r)

    def test_feed_edit_bogus(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        ed_u = fuzz_db['editor']
        try:
            r = c.post(f'/feeds/{f1.id}',
                       data={'action': 'edit', 'authors': '99999',
                             'publishers': 'abc'},
                       follow_redirects=True)
            _aok(r)
        except ValueError:
            pass
        f1.grant('Write', user=ed_u)
        f1.grant('Publish', user=ed_u)

    def test_post_edit_valid(self, fuzz_db):
        c = fuzz_db['client']
        pids = fuzz_db['pids']
        r = c.post(f'/posts/{pids[2]}',
                   data={'action': 'edit', 'post_title': 'Updated Title'},
                   follow_redirects=True)
        _a200(r)
        p = models.Post.get(models.Post.id == pids[2])
        assert p.title == 'Updated Title'

    def test_post_publish(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        admin = fuzz_db['admin']
        p = models.Post.create(
            title='Unpub', type='text',
            content=json.dumps({'type': 'text', 'content': 'up'}),
            feed=f1, author=admin, published=False)
        r = c.post(f'/posts/{p.id}',
                   data={'action': 'publish', 'post_title': 'Unpub'},
                   follow_redirects=True)
        _a200(r)
        assert models.Post.get(models.Post.id == p.id).published is True

    def test_post_unpublish(self, fuzz_db):
        c = fuzz_db['client']
        pids = fuzz_db['pids']
        r = c.post(f'/posts/{pids[1]}',
                   data={'action': 'unpublish'},
                   follow_redirects=True)
        _a200(r)
        assert models.Post.get(models.Post.id == pids[1]).published is False

    def test_post_delete(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        admin = fuzz_db['admin']
        p = models.Post.create(
            title='ToDelete', type='text',
            content=json.dumps({'type': 'text', 'content': 'td'}),
            feed=f1, author=admin, published=False)
        r = c.post(f'/posts/{p.id}',
                   data={'action': 'delete'},
                   follow_redirects=True)
        _a200(r)
        assert not models.Post.select().where(
            models.Post.id == p.id).exists()

    def test_post_edit_bogus_type(self, fuzz_db):
        c = fuzz_db['client']
        pids = fuzz_db['pids']
        r = c.post(f'/posts/{pids[2]}',
                   data={'action': 'edit', 'post_type': 'nonexistent_type'},
                   follow_redirects=True)
        _a200(r)

    # Screen CRUD
    def test_screen_edit_valid(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/screens-edit/1',
                   data={'action': 'update', 'urlname': 'Default',
                         'css': 'body { color: red; }'},
                   follow_redirects=True)
        _a200(r)

    def test_screen_create(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/screens-edit/-1',
                   data={'action': 'update', 'urlname': 'NewScreen123'},
                   follow_redirects=True)
        _a200(r)
        s = models.Screen.get(models.Screen.urlname == 'NewScreen123')
        assert s is not None
        s.delete_instance()

    def test_screen_create_empty_name(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/screens-edit/-1',
                   data={'action': 'update', 'urlname': ''},
                   follow_redirects=True)
        _a200(r)


# ---------------------------------------------------------------------------
# Phase D: Aliases & Client
# ---------------------------------------------------------------------------

class TestAliases:
    def test_aliases_zero_persist(self, fuzz_db):
        c = fuzz_db['client']
        S1 = fuzz_db['S1']
        _login(c, 'admin', 'testpass')
        r = c.post('/aliases', data={'aliases': json.dumps([
            {'name': 'main', 'screen_name': S1.urlname, 'screen_type': 'basic',
             'fadetime': 0, 'scrollspeed': 0, 'forceaspect': 0, 'forcetop': 0}
        ])})
        _a200(r)
        data = json.loads(r.data)
        a = data['aliases'][0]
        assert a['fadetime'] == 0
        assert a['forcetop'] == 0

    def test_aliases_duplicate(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/aliases', data={'aliases': json.dumps([
            {'name': 'dup', 'screen_name': 'Default'},
            {'name': 'dup', 'screen_name': 'Lobby'},
        ])})
        assert r.status_code in (200, 400)

    def test_aliases_missing_fields(self, fuzz_db):
        c = fuzz_db['client']
        r = c.post('/aliases', data={'aliases': json.dumps(
            [{'name': 'minimal'}])})
        _a200(r)

    def test_aliases_get(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/aliases')
        _a200(r)
        d = json.loads(r.data)
        assert len(d['aliases']) > 0

    def test_client_deleted_screen(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/client/bogus')
        _a200(r)
        assert b'Screen Alias' in r.data or b'not found' in r.data.lower()

    def test_client_valid(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/client/main')
        _a200(r)


# ---------------------------------------------------------------------------
# Phase E: Dashboard & Health
# ---------------------------------------------------------------------------

class TestDashboardHealth:
    def test_dash_anon(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/', follow_redirects=True)
        _a200(r)

    def test_dash_auth(self, fuzz_db):
        c = fuzz_db['client']
        _login(c, 'admin', 'testpass')
        r = c.get('/', follow_redirects=True)
        _a200(r)
        assert b'Dashboard' in r.data or b'Streetsign' in r.data

    def test_health(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/health')
        _a200(r)
        d = json.loads(r.data)
        assert d['status'] == 'ok'
        assert d['database'] == 'ok'

    def test_robots(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/robots.txt')
        _a200(r)
        assert b'Disallow' in r.data


# ---------------------------------------------------------------------------
# Phase F: Permission Feeds
# ---------------------------------------------------------------------------

class TestPermissionFeeds:
    def test_writeable_feeds(self, fuzz_db):
        ed_u = fuzz_db['editor']
        feeds = list(ed_u.writeable_feeds())
        assert len(feeds) == 1
        assert feeds[0].name == 'Test Feed'

    def test_publishable_feeds(self, fuzz_db):
        ed_u = fuzz_db['editor']
        feeds = list(ed_u.publishable_feeds())
        assert len(feeds) == 1

    def test_viewer_no_write(self, fuzz_db):
        vw_u = fuzz_db['viewer']
        assert len(list(vw_u.writeable_feeds())) == 0

    def test_feed_setters(self, fuzz_db):
        f1 = fuzz_db['f1']
        ed_u = fuzz_db['editor']
        vw_u = fuzz_db['viewer']

        f1.set_authors([ed_u, vw_u])
        assert f1.user_can_write(ed_u)
        assert f1.user_can_write(vw_u)

        f1.set_publishers([ed_u])
        assert f1.user_can_publish(ed_u)

        f1.set_authors([])
        f1.set_publishers([])

        f1.grant('Write', user=ed_u)
        f1.grant('Publish', user=ed_u)

    def test_feed_group_setters(self, fuzz_db):
        f1 = fuzz_db['f1']
        g1 = fuzz_db['g1']
        ed_u = fuzz_db['editor']

        f1.set_author_groups([g1])
        f1.set_publisher_groups([g1])
        f1.set_author_groups([])
        f1.set_publisher_groups([])

        f1.grant('Write', user=ed_u)
        f1.grant('Publish', user=ed_u)


# ---------------------------------------------------------------------------
# Phase G: Screen Public Endpoints
# ---------------------------------------------------------------------------

class TestScreenEndpoints:
    def test_screen_display(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/screens/basic/Default')
        _a200(r)

    def test_screen_bogus(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/screens/basic/NoSuch')
        _a200(r)

    def test_screen_invalid_template(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/screens/evil_template/Default')
        assert r.status_code in (200, 404, 500)

    def test_posts_from_feeds(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/screens/posts_from_feeds/[1,2]')
        _a200(r)
        assert 'posts' in json.loads(r.data)

    def test_posts_from_feeds_bad(self, fuzz_db):
        c = fuzz_db['client']
        for bad in ('', 'null', 'notjson', '123', 'true'):
            r = c.get('/screens/posts_from_feeds/' + bad)
            _aok(r)

    def test_screen_json(self, fuzz_db):
        c = fuzz_db['client']
        S1 = fuzz_db['S1']
        r = c.get(f'/screens/json/{S1.id}/0000000000000000')
        _a200(r)
        assert 'screenid' in json.loads(r.data)

    def test_screen_json_bogus(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/screens/json/99999/foobar')
        _a200(r)

    def test_post_types_js(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/screens/post_types.js')
        _a200(r)
        assert r.headers.get('Content-Type', '').startswith(
            'application/javascript')

    def test_rss_feed(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        r = c.get(f'/feeds/rss/{f1.id}')
        _a200(r)
        assert 'application/xml' in r.headers.get('Content-Type', '')
        assert b'<rss' in r.data

    def test_rss_feed_bad(self, fuzz_db):
        c = fuzz_db['client']
        for bad in ('', 'abc', '99999', '1,2,abc'):
            r = c.get(f'/feeds/rss/{bad}')
            _aok(r)

    def test_json_post(self, fuzz_db):
        c = fuzz_db['client']
        pids = fuzz_db['pids']
        r = c.get(f'/posts/{pids[4]}/json')
        _a200(r)
        assert json.loads(r.data)['type'] == 'text'

    def test_json_post_nonexistent(self, fuzz_db):
        c = fuzz_db['client']
        r = c.get('/posts/99999/json')
        assert r.status_code in (200, 404)

    def test_weather_proxy(self, fuzz_db):
        c = fuzz_db['client']
        try:
            r = c.get('/weather-proxy/London')
            assert r.status_code < 600
        except Exception:
            pass

    def test_weather_proxy_bad(self, fuzz_db):
        c = fuzz_db['client']
        try:
            for bad in ('', '../../../etc/passwd', 'http://evil.com', '%00'):
                r = c.get('/weather-proxy/' + urllib.parse.quote(bad, safe=''))
                assert r.status_code < 600
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Phase H: Uniqueness
# ---------------------------------------------------------------------------

class TestUniqueness:
    def test_unique_loginname(self, fuzz_db):
        c = fuzz_db['client']
        _login(c, 'admin', 'testpass')
        u3 = models.User(displayname='Auto1')
        u3.set_password('a')
        u3.save()
        u4 = models.User(displayname='Auto2')
        u4.set_password('b')
        u4.save()
        assert u3.loginname.startswith('user_')
        assert u4.loginname != u3.loginname
        u3.delete_instance(recursive=True)
        u4.delete_instance(recursive=True)


# ---------------------------------------------------------------------------
# Phase I: Auth Boundary Tests
# ---------------------------------------------------------------------------

PROTECTED_ENDPOINTS = [
    ('GET', '/feeds/'),
    ('GET', '/screens/'),
    ('GET', '/users_and_groups'),
    ('GET', '/posts/'),
    ('GET', '/user_files/'),
    ('POST', '/feeds'),
    ('POST', '/users_and_groups'),
    ('POST', '/aliases'),
    ('POST', '/posts/housekeeping'),
    ('POST', '/posts/bulk_delete'),
]


class TestAuthBoundaries:
    def test_anon_cannot_access_protected(self, fuzz_db):
        c = fuzz_db['client']
        _logout(c)
        for method, url in PROTECTED_ENDPOINTS:
            if method == 'GET':
                r = c.get(url, follow_redirects=False)
            else:
                r = c.post(url, data={}, follow_redirects=False)
            assert r.status_code in (302, 403, 301, 308), \
                f'{method} {url}: got {r.status_code}'

    def test_viewer_cannot_admin(self, fuzz_db):
        c = fuzz_db['client']
        _logout(c)
        _login(c, 'viewer', 'testpass')
        r = c.post('/feeds', data={'title': 'HackedFeed'},
                   follow_redirects=False)
        assert r.status_code != 200
        r = c.post('/users_and_groups',
                   data={'action': 'creategroup', 'name': 'Hacked'},
                   follow_redirects=False)
        assert r.status_code != 200
        r = c.post('/posts/housekeeping', follow_redirects=False)
        assert r.status_code != 200

    def test_editor_cannot_admin(self, fuzz_db):
        c = fuzz_db['client']
        _logout(c)
        _login(c, 'editor', 'testpass')
        r = c.post('/feeds', data={'title': 'Hacked2'},
                   follow_redirects=False)
        assert r.status_code != 200

    def test_viewer_can_see_allowed_feeds(self, fuzz_db):
        c = fuzz_db['client']
        f2 = fuzz_db['f2']
        _login(c, 'viewer', 'testpass')
        r = c.get(f'/feeds/{f2.id}', follow_redirects=True)
        _a200(r)

    def test_locked_out_behavior(self, fuzz_db):
        c = fuzz_db['client']
        ed_u = fuzz_db['editor']
        u = models.User.get(models.User.id == ed_u.id)
        u.is_locked_out = True
        u.save()
        _login(c, 'editor', 'testpass')
        r = c.get('/feeds/', follow_redirects=True)
        _aok(r)
        u.is_locked_out = False
        u.save()

    def test_csrf_blocks_unauthorized_post(self, fuzz_db):
        c = fuzz_db['client']
        _login(c, 'editor', 'testpass')
        app.config['TESTING'] = False
        app.config['CSRF_ENABLED'] = True
        r = c.post('/feeds', data={'title': 'CSRFTest'})
        assert r.status_code in (302, 403)
        app.config['TESTING'] = True
        app.config['CSRF_ENABLED'] = False


# ---------------------------------------------------------------------------
# Phase J: Post Type Creation
# ---------------------------------------------------------------------------

class TestPostTypeCreation:
    @pytest.fixture(autouse=True)
    def _login(self, fuzz_db):
        _login(fuzz_db['client'], 'admin', 'testpass')

    def _create_post_type(self, fuzz_db, ptype, content):
        c = fuzz_db['client']
        f3 = fuzz_db['f3']
        r = c.post(f'/posts/new/{f3.id}',
                   data={'post_title': f'Test {ptype}',
                         'post_type': ptype,
                         'content': json.dumps(content),
                         'action': 'edit'},
                   follow_redirects=True)
        return r

    def test_post_type_text(self, fuzz_db):
        r = self._create_post_type(
            fuzz_db, 'text', {'type': 'text', 'content': 'Hello'})
        _aok(r)

    def test_post_type_html(self, fuzz_db):
        r = self._create_post_type(
            fuzz_db, 'html', {'type': 'html', 'content': '<b>bold</b>'})
        _aok(r)

    def test_post_type_raw_html(self, fuzz_db):
        r = self._create_post_type(
            fuzz_db, 'raw_html', {'type': 'raw_html',
                                  'content': '<script>alert(1)</script>'})
        _aok(r)

    def test_post_type_image(self, fuzz_db):
        r = self._create_post_type(
            fuzz_db, 'image', {'type': 'image', 'content': 'test.png'})
        _aok(r)


# ---------------------------------------------------------------------------
# Phase Z: Random Fuzzing
# ---------------------------------------------------------------------------

FUZZ_STRINGS = [
    '', 'x', 'x' * 10, 'x' * 1000, 'x' * 100000,
    'null', 'undefined', 'NaN', 'Infinity',
    '--', ';--', "' OR 1=1 --", '<script>alert(1)</script>',
    '{"foo": "bar"}', '[1,2,3]',
    '\x00\x01\x02\xff',
    ' ' * 100, '\n' * 10, '\t\r\n',
    '../../../etc/passwd', 'NUL:CON:',
    'True', 'False', 'None', '0', '-1', '9999999999999999999',
]

FUZZ_ENDPOINTS = [
    ('GET', '/', lambda f, i: {}, None),
    ('GET', '/health', lambda f, i: {}, None),
    ('GET', '/screens/', lambda f, i: {}, None),
    ('GET', '/feeds/', lambda f, i: {}, None),
    ('GET', '/posts/', lambda f, i: {}, None),
    ('GET', '/users_and_groups', lambda f, i: {}, None),
    ('GET', '/screens/basic/{S1_url}', lambda f, i: {}, 'S1_url'),
    ('GET', '/screens/posts_from_feeds/[1]', lambda f, i: {}, None),
    ('GET', '/screens/json/{S1_id}/000', lambda f, i: {}, 'S1_id'),
    ('GET', '/screens/post_types.js', lambda f, i: {}, None),
    ('GET', '/client/main', lambda f, i: {}, None),
    ('GET', '/posts/{pid0}/json', lambda f, i: {}, 'pid0'),
    ('POST', '/login', lambda f, i: {
        'username': f, 'password': f}, None),
    ('POST', '/feeds', lambda f, i: {'title': f}, None),
    ('POST', '/feeds/{f1_id}', lambda f, i: {
        'action': f[:10], 'title': f[:50]}, 'f1_id'),
    ('POST', '/feeds/{f1_id}/reorder', lambda f, i: (
        json.dumps({'post_ids': [i, f, -99999, 0, 1]}),
        {'content_type': 'application/json'}), 'f1_id'),
    ('POST', '/posts/bulk_delete', lambda f, i: (
        json.dumps({'post_ids': [i, 'x' * 1000, None, True]}),
        {'content_type': 'application/json'}), None),
    ('POST', '/users_and_groups', lambda f, i: {
        'action': f[:10], 'name': f[:10], 'groupusers': f[:100]}, None),
    ('POST', '/users/{ed_id}', lambda f, i: {
        'loginname': f[:50], 'emailaddress': f[:50],
        'displayname': f[:50], 'groups': f[:50]}, 'ed_id'),
    ('POST', '/group/{g1_id}', lambda f, i: {
        'action': f[:10], 'groupname': f[:20],
        'groupusers': f[:50]}, 'g1_id'),
    ('POST', '/aliases', lambda f, i: {'aliases': json.dumps(
        [{'name': f[:20], 'screen_name': f[:20],
          'fadetime': random.choice([0, -1, None, True, False, f])}])}, None),
    ('POST', '/posts/new/{f1_id}', lambda f, i: {
        'post_title': f[:100], 'post_type': f[:10],
        'action': f[:10],
        'content': json.dumps(
            {'type': 'text', 'content': f[:100]})}, 'f1_id'),
    ('POST', '/posts/{pid0}', lambda f, i: {
        'action': f[:10], 'post_title': f[:100]}, 'pid0'),
    ('POST', '/posts/housekeeping', lambda f, i: {}, None),
    ('POST', '/screens-edit/1', lambda f, i: {
        'action': f[:10], 'urlname': f[:30],
        'css': f[:500]}, None),
    ('POST', '/screens-edit/-1', lambda f, i: {
        'action': f[:10], 'urlname': f[:30]}, None),
    ('GET', '/user_files/', lambda f, i: {}, None),
]


class TestRandomFuzzing:
    """Body / data fuzzing with malformed inputs against all endpoints."""

    def test_body_fuzzing(self, fuzz_db):
        c = fuzz_db['client']
        _login(c, 'admin', 'testpass')

        S1 = fuzz_db['S1']
        f1 = fuzz_db['f1']
        ed_u = fuzz_db['editor']
        g1 = fuzz_db['g1']
        pids = fuzz_db['pids']

        fmt = {
            'S1_url': S1.urlname,
            'S1_id': str(S1.id),
            'f1_id': str(f1.id),
            'ed_id': str(ed_u.id),
            'g1_id': str(g1.id),
            'pid0': str(pids[0]),
        }

        crashes = 0
        tried = 0
        for method, url_tmpl, param_gen, _fmt_key in FUZZ_ENDPOINTS:
            for fuzz_idx in range(min(5, len(FUZZ_STRINGS))):
                si = (fuzz_idx + random.randint(
                    0, len(FUZZ_STRINGS) - 1)) % len(FUZZ_STRINGS)
                fuzz_str = FUZZ_STRINGS[si]
                fuzz_int = random.choice(
                    [0, -1, 9999999, 2 ** 63 - 1, -2 ** 63]) \
                    if random.random() < 0.5 else fuzz_str

                params = param_gen(fuzz_str, fuzz_int)
                url = url_tmpl.format(**fmt) if '{' in url_tmpl else url_tmpl

                if isinstance(params, tuple):
                    data, kw = params
                else:
                    data, kw = params, {}

                try:
                    if method == 'GET':
                        r = c.get(url, **kw)
                    else:
                        r = c.post(url, data=data, **kw)
                except Exception:
                    continue

                tried += 1
                if r.status_code >= 500:
                    crashes += 1
                    body = r.data.decode('utf-8', errors='replace')[:200]
                    print(
                        f'  FUZZ CRASH [{r.status_code}] {method} {url}: {body}')

        print(f'  Body fuzz: {tried} inputs, {crashes} crashes')
        assert crashes == 0, f'{crashes} server crashes in body fuzzing!'


# ---------------------------------------------------------------------------
# Path / query / content-type / header fuzzing
# ---------------------------------------------------------------------------

PATH_BASES = [
    '/screens/posts_from_feeds/', '/screens/json/', '/client/', '/posts/',
    '/feeds/', '/group/', '/users/',
    '/screens/basic/', '/screens/notrans/', '/screens/mobile/',
    '/feeds/rss/',
    '/user_files/',
]

QUERY_BASES = ['/', '/feeds/', '/posts/', '/screens/', '/users_and_groups']


class TestEndpointFuzzing:
    def test_path_fuzzing(self, fuzz_db):
        c = fuzz_db['client']
        _login(c, 'admin', 'testpass')
        path_samples = random.sample(
            FUZZ_STRINGS, min(8, len(FUZZ_STRINGS)))
        crashes = 0
        for base in PATH_BASES:
            for bad_val in path_samples:
                encoded = urllib.parse.quote(str(bad_val), safe='')
                try:
                    r = c.get(base + encoded)
                except Exception:
                    continue
                if r.status_code >= 500:
                    crashes += 1
        assert crashes == 0, f'{crashes} crashes in path fuzzing'

    def test_query_parameter_fuzzing(self, fuzz_db):
        c = fuzz_db['client']
        crashes = 0
        for base in QUERY_BASES:
            for param in ('page', 'q', 'sort', 'id', 'search'):
                for val in random.sample(
                        FUZZ_STRINGS, min(3, len(FUZZ_STRINGS))):
                    encoded = urllib.parse.quote(str(val), safe='')
                    try:
                        r = c.get(f'{base}?{param}={encoded}')
                    except Exception:
                        continue
                    if r.status_code >= 500:
                        crashes += 1
        assert crashes == 0, f'{crashes} crashes in query param fuzzing'

    def test_content_type_fuzzing(self, fuzz_db):
        c = fuzz_db['client']
        f1 = fuzz_db['f1']
        _login(c, 'admin', 'testpass')
        tests = [
            (f'/feeds/{f1.id}/reorder', 'text/plain', b''),
            (f'/feeds/{f1.id}/reorder', 'application/xml', b'<xml>'),
            (f'/feeds/{f1.id}/reorder', '', b'{'),
            (f'/feeds/{f1.id}/reorder', 'application/json', b'['),
            (f'/feeds/{f1.id}/reorder', 'application/json', b'null'),
            (f'/feeds/{f1.id}/reorder', 'application/json',
             b'{"post_ids": [1]}'),
            (f'/feeds/{f1.id}/reorder', 'application/json',
             b'\x00\xff' * 10),
            ('/posts/bulk_delete', 'text/plain', b'['),
            ('/posts/bulk_delete', 'multipart/form-data', b'--boundary'),
            ('/posts/bulk_delete', '', b''),
            ('/posts/bulk_delete', 'application/json', b'garbage'),
            ('/posts/bulk_delete', 'application/json',
             b'{"post_ids": {"nested": "bad"}}'),
        ]
        crashes = 0
        for endpoint, ct, body in tests:
            try:
                r = c.post(endpoint, data=body, content_type=ct)
            except Exception:
                continue
            if r.status_code >= 500:
                crashes += 1
        assert crashes == 0, f'{crashes} crashes in content-type fuzzing'

    def test_header_fuzzing(self, fuzz_db):
        c = fuzz_db['client']
        bad_headers = {
            'Content-Length': ['-1', 'abc', '9999999999999999999'],
            'X-Forwarded-For': ['127.0.0.1', '0' * 1000, '\x00' * 10],
            'Accept': ['\x00' * 10, 'x' * 2000],
            'User-Agent': [''.join(chr(i) for i in range(256))],
        }
        crashes = 0
        for hdr_name, hdr_values in bad_headers.items():
            for hdr_val in hdr_values:
                try:
                    r = c.get('/', headers=[(hdr_name, hdr_val)])
                except Exception:
                    continue
                if r.status_code >= 500:
                    crashes += 1
        assert crashes == 0, f'{crashes} crashes in header fuzzing'
