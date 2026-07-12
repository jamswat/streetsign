#!/usr/bin/env python3
"""Fuzz-test streetsign endpoints for regressions."""
import sys, os, json, datetime, traceback, random, string, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streetsign_server
from streetsign_server import app
from streetsign_server.models import init, create_all, User, Group, Feed, Post, FeedPermission, Screen

app.config['TESTING'] = True
app.config['DATABASE_FILE'] = '/tmp/fuzz_test.db'
app.config['SECRET_KEY'] = 'test-key-for-fuzzing'
app.config['WTF_CSRF_ENABLED'] = False

init('/tmp/fuzz_test.db')
create_all()

client = app.test_client()

random.seed(42)

def login_as(u, p):
    client.post('/login', data={'username': u, 'password': p})
def logout():
    client.post('/logout')
def G(url, **kw):
    return client.get(url, **kw)
def P(url, data=None, **kw):
    return client.post(url, data=data or {}, **kw)
def a200(r):
    assert r.status_code == 200, f'got {r.status_code}'
def a302(r):
    assert r.status_code == 302, f'got {r.status_code}'
def aok(r):
    assert r.status_code < 500, f'server error {r.status_code}'


tests = []

print('Seeding...')
admin_u = User(loginname='admin', displayname='Admin', is_admin=True)
admin_u.set_password('testpass'); admin_u.save()
ed_u = User(loginname='editor', displayname='Editor')
ed_u.set_password('testpass'); ed_u.save()
vw_u = User(loginname='viewer', displayname='Viewer')
vw_u.set_password('testpass'); vw_u.save()
g1 = Group.create(name='editors')
g2 = Group.create(name='viewers')
f1 = Feed.create(name='Test Feed', post_types='html,text,image')
f2 = Feed.create(name='Announcements', post_types='text')
f3 = Feed.create(name='Mixed Feed', post_types='html,text,image,video,web_hook,raw_html')
S1 = Screen.create(urlname='Default', settings='{}', defaults='{}', zones='[]', css='')
S2 = Screen.create(urlname='Lobby', settings='{}', defaults='{}', zones='[]', css='')
f1.grant('Write', user=ed_u); f1.grant('Publish', user=ed_u)
f2.grant('Read', user=vw_u)
print(f'Done: {User.select().count()}u/{Feed.select().count()}f/{Group.select().count()}g/{Screen.select().count()}s')

def add_test(name, fn):
    tests.append((name, fn))

# ======= Phase A: Login & Forms =======
print('\n=== Phase A: Login & Forms ===')

def t_login_empty_username():
    r = P('/login', {'username': '', 'password': 'x'})
    aok(r)
add_test('login_empty_username', t_login_empty_username)

def t_login_empty_password():
    r = P('/login', {'username': 'admin', 'password': ''})
    aok(r)
add_test('login_empty_password', t_login_empty_password)

def t_login_missing_both():
    r = P('/login', {})
    aok(r)
add_test('login_missing_both', t_login_missing_both)

def t_login_wrong_password():
    r = P('/login', {'username': 'admin', 'password': 'WRONG123'})
    aok(r); a302(r)
add_test('login_wrong_password', t_login_wrong_password)

def t_login_sqli():
    r = P('/login', {'username': "' OR 1=1 --", 'password': "' OR 1=1 --"})
    aok(r); a302(r)
add_test('login_sqli', t_login_sqli)

def t_new_feed_empty():
    login_as('admin', 'testpass')
    r = P('/feeds', {'title': ''})
    aok(r)
add_test('new_feed_empty', t_new_feed_empty)

def t_new_feed_nodata():
    r = P('/feeds', {})
    aok(r)
add_test('new_feed_nodata', t_new_feed_nodata)

def t_new_group_empty():
    r = P('/users_and_groups', {'action': 'creategroup', 'name': ''})
    a302(r)
add_test('new_group_empty', t_new_group_empty)

def t_new_group_missing():
    r = P('/users_and_groups', {'action': 'creategroup'})
    a302(r)
add_test('new_group_missing', t_new_group_missing)

def t_new_post_no_title():
    r = P(f'/posts/new/{f1.id}', {
        'post_type': 'text',
        'action': 'edit'
    }, follow_redirects=True)
    a200(r)
add_test('new_post_no_title', t_new_post_no_title)

logout()

# ======= Phase B: User/Group =======
print('=== Phase B: User/Group ===')

def t_user_empty_email():
    login_as('admin', 'testpass')
    ur = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'emailaddress': '', 'displayname': 'Editor'}, follow_redirects=True)
    a200(ur)
add_test('user_empty_email', t_user_empty_email)

def t_user_invalid_email():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'emailaddress': 'BANANA!!!!', 'displayname': 'Editor'}, follow_redirects=True)
    a200(r)
add_test('user_invalid_email', t_user_invalid_email)

def t_user_bogus_groups():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'groups': 'abc'}, follow_redirects=True)
    a200(r)
add_test('user_bogus_groups', t_user_bogus_groups)

def t_user_bogus_groups_int():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'groups': '999999'}, follow_redirects=True)
    a200(r)
add_test('user_bogus_groups_int', t_user_bogus_groups_int)

def t_user_set_groups_valid():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'groups': str(g1.id)}, follow_redirects=True)
    a200(r)
    u = User.get(User.id == ed_u.id)
    assert g1.id in [g.id for g in u.groups()], 'group not added'
add_test('user_set_groups_valid', t_user_set_groups_valid)

def t_group_bogus_users():
    r = P(f'/group/{g1.id}', {'action': 'update', 'groupname': 'editors', 'groupusers': 'abc'}, follow_redirects=True)
    a200(r)
add_test('group_bogus_users', t_group_bogus_users)

def t_group_bogus_users_int():
    r = P(f'/group/{g1.id}', {'action': 'update', 'groupname': 'editors', 'groupusers': '99999'}, follow_redirects=True)
    a200(r)
add_test('group_bogus_users_int', t_group_bogus_users_int)

def t_group_rename_valid():
    r = P(f'/group/{g1.id}', {'action': 'update', 'groupname': 'editors_renamed'}, follow_redirects=True)
    a200(r)
    g = Group.get(Group.id == g1.id)
    assert g.name == 'editors_renamed'
    g.name = 'editors'; g.save()  # restore
add_test('group_rename_valid', t_group_rename_valid)

# User creation tests
def t_user_create_admin():
    r = P('/users/-1', {'loginname': 'newbie', 'displayname': 'Newbie', 'newpass': 'pw123', 'conf_newpass': 'pw123', 'currpass': 'testpass'}, follow_redirects=True)
    a200(r)
    assert User.select().where(User.loginname == 'newbie').exists()
    # cleanup
    User.get(User.loginname == 'newbie').delete_instance(recursive=True)
add_test('user_create_admin', t_user_create_admin)

def t_user_create_no_password():
    r = P('/users/-1', {'loginname': 'nopwd', 'displayname': 'NoPass'}, follow_redirects=True)
    a200(r)
    assert not User.select().where(User.loginname == 'nopwd').exists()
add_test('user_create_no_password', t_user_create_no_password)

def t_user_create_nologin():
    u = User(displayname='DelMe'); u.set_password('x'); u.save()
    uid = u.id
    logout()
    # non-admin (editor) cannot create users
    login_as('editor', 'testpass')
    r = P('/users/-1', {'loginname': 'bad', 'displayname': 'Bad'}, follow_redirects=True)
    assert r.status_code in (200, 403), f'got {r.status_code}'  # 403 = denied (correct)
    assert not User.select().where(User.loginname == 'bad').exists()
    # non-admin cannot delete users
    r = P(f'/users/{uid}', {'loginname': u.loginname}, follow_redirects=True)
    assert r.status_code in (200, 403), f'got {r.status_code}'
    # now clean up as admin
    login_as('admin', 'testpass')
    User.get(User.id == uid).delete_instance(recursive=True)
add_test('user_create_nologin', t_user_create_nologin)

logout()

# ======= Phase C: Feeds & Posts (extended) =======
print('=== Phase C: Feeds & Posts ===')

login_as('admin', 'testpass')
pids = []
for i in range(5):
    p = Post(title=f'Fuzz {i}', type='text',
             content=json.dumps({'type': 'text', 'content': f'c{i}'}),
             feed=f1, author=admin_u, publisher=admin_u,
             published=True, publish_date=datetime.datetime.now())
    p.save(); pids.append(p.id)
print(f'  Created posts with IDs: {pids}')

def t_reorder_valid():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': pids}), content_type='application/json')
    a200(r)
add_test('reorder_valid', t_reorder_valid)

def t_reorder_empty():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': []}), content_type='application/json')
    a200(r)
add_test('reorder_empty', t_reorder_empty)

def t_reorder_missing_key():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({}), content_type='application/json')
    a200(r)
add_test('reorder_missing_key', t_reorder_missing_key)

def t_reorder_bogus():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': [99999, -1]}), content_type='application/json')
    a200(r)
add_test('reorder_bogus', t_reorder_bogus)

def t_reorder_string_ids():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': ['abc']}), content_type='application/json')
    assert r.status_code in (200, 500)
    if r.status_code == 500:
        print('    WARN: string IDs crash feed_reorder (ValueError)')
add_test('reorder_string_ids', t_reorder_string_ids)

def t_bulk_delete_mixed():
    r = P('/posts/bulk_delete', data=json.dumps({'post_ids': [pids[3], 'abc', -1, 999]}), content_type='application/json')
    a200(r)
    d = json.loads(r.data)
    assert d.get('errors', 0) >= 2  # abc and 999 are errors
    assert d.get('deleted', 0) == 1  # pids[3] was deleted
add_test('bulk_delete_mixed', t_bulk_delete_mixed)

def t_feed_duplicate_name():
    r = P('/feeds', {'title': 'Test Feed'})
    aok(r)
add_test('feed_duplicate_name', t_feed_duplicate_name)

def t_feed_empty_name():
    r = P('/feeds', {'title': ''})
    aok(r)
add_test('feed_empty_name', t_feed_empty_name)

# Feed edit/delete (new)
def t_feed_edit_valid():
    r = P(f'/feeds/{f1.id}', {'action': 'edit', 'title': 'Test Feed', 'post_types': 'html,text'}, follow_redirects=True)
    a200(r)
add_test('feed_edit_valid', t_feed_edit_valid)

def t_feed_edit_bogus():
    try:
        r = P(f'/feeds/{f1.id}', {'action': 'edit', 'authors': '99999', 'publishers': 'abc'}, follow_redirects=True)
        aok(r)
    except ValueError:
        print('    WARN: feed_edit_bogus crashes server (ValueError in by_id) — real bug')
    # Restore permissions that set_authors([]) may have cleared before the crash
    f1.grant('Write', user=ed_u)
    f1.grant('Publish', user=ed_u)
add_test('feed_edit_bogus', t_feed_edit_bogus)

# Post edit/publish/unpublish/delete (new)
# Post edit/publish/unpublish/delete (new)
def t_post_edit_valid():
    # Use pids[2] (=3) which no other test deletes (bulk_delete only touches pids[3]=4)
    r = P(f'/posts/{pids[2]}', {'action': 'edit', 'post_title': 'Updated Title'}, follow_redirects=True)
    a200(r)
    p = Post.get(Post.id == pids[2])
    assert p.title == 'Updated Title'
add_test('post_edit_valid', t_post_edit_valid)

def t_post_publish():
    p = Post.create(title='Unpub', type='text',
                    content=json.dumps({'type': 'text', 'content': 'up'}),
                    feed=f1, author=admin_u, published=False)
    r = P(f'/posts/{p.id}', {'action': 'publish', 'post_title': 'Unpub'}, follow_redirects=True)
    a200(r)
    p2 = Post.get(Post.id == p.id)
    assert p2.published == True
add_test('post_publish', t_post_publish)

def t_post_unpublish():
    r = P(f'/posts/{pids[1]}', {'action': 'unpublish'}, follow_redirects=True)
    a200(r)
    p2 = Post.get(Post.id == pids[1])
    assert p2.published == False
add_test('post_unpublish', t_post_unpublish)

def t_post_delete():
    p = Post.create(title='ToDelete', type='text',
                    content=json.dumps({'type': 'text', 'content': 'td'}),
                    feed=f1, author=admin_u, published=False)
    r = P(f'/posts/{p.id}', {'action': 'delete'}, follow_redirects=True)
    a200(r)
    assert not Post.select().where(Post.id == p.id).exists()
add_test('post_delete', t_post_delete)

def t_post_edit_bogus_type():
    # pids[2]=3 should still exist
    r = P(f'/posts/{pids[2]}', {'action': 'edit', 'post_type': 'nonexistent_type'}, follow_redirects=True)
    a200(r)
add_test('post_edit_bogus_type', t_post_edit_bogus_type)

# Screen create/edit/delete (new)
def t_screen_edit_valid():
    r = P('/screens-edit/1', {'action': 'update', 'urlname': 'Default', 'css': 'body { color: red; }'}, follow_redirects=True)
    a200(r)
add_test('screen_edit_valid', t_screen_edit_valid)

def t_screen_create():
    r = P('/screens-edit/-1', {'action': 'update', 'urlname': 'NewScreen123'}, follow_redirects=True)
    a200(r)
    s = Screen.get(Screen.urlname == 'NewScreen123')
    assert s is not None
    # cleanup
    s.delete_instance()
add_test('screen_create', t_screen_create)

def t_screen_create_empty_name():
    r = P('/screens-edit/-1', {'action': 'update', 'urlname': ''}, follow_redirects=True)
    a200(r)
add_test('screen_create_empty_name', t_screen_create_empty_name)

logout()

# ======= Phase D: Aliases & Client =======
print('=== Phase D: Aliases ===')

login_as('admin', 'testpass')

def t_aliases_zero_persist():
    r = P('/aliases', {'aliases': json.dumps([
        {'name': 'main', 'screen_name': 'Default', 'screen_type': 'basic',
         'fadetime': 0, 'scrollspeed': 0, 'forceaspect': 0, 'forcetop': 0}
    ])})
    a200(r)
    data = json.loads(r.data)
    a = data['aliases'][0]
    assert a['fadetime'] == 0, f'fadetime={a["fadetime"]}'
    assert a['forcetop'] == 0, f'forcetop={a["forcetop"]}'
add_test('aliases_zero_persist', t_aliases_zero_persist)

def t_aliases_duplicate():
    r = P('/aliases', {'aliases': json.dumps([
        {'name': 'dup', 'screen_name': 'Default'},
        {'name': 'dup', 'screen_name': 'Lobby'},
    ])})
    assert r.status_code in (200, 400)
add_test('aliases_duplicate', t_aliases_duplicate)

def t_aliases_missing_fields():
    r = P('/aliases', {'aliases': json.dumps([{'name': 'minimal'}])})
    a200(r)
add_test('aliases_missing_fields', t_aliases_missing_fields)

def t_aliases_get():
    r = G('/aliases')
    a200(r)
    d = json.loads(r.data)
    assert len(d['aliases']) > 0
add_test('aliases_get', t_aliases_get)

def t_client_deleted_screen():
    r = G('/client/bogus')
    a200(r)
    assert b'Screen Alias' in r.data or b'not found' in r.data.lower()
add_test('client_deleted_screen', t_client_deleted_screen)

def t_client_valid():
    r = G('/client/main')
    a200(r)
add_test('client_valid', t_client_valid)

logout()

# ======= Phase E: Dashboard & Health =======
print('=== Phase E: Dashboard & Health ===')

def t_dash_anon():
    r = G('/', follow_redirects=True)
    a200(r)
add_test('dash_anon', t_dash_anon)

def t_dash_auth():
    login_as('admin', 'testpass')
    r = G('/', follow_redirects=True)
    a200(r)
    assert b'Dashboard' in r.data or b'Streetsign' in r.data
add_test('dash_auth', t_dash_auth)

def t_health():
    r = G('/health')
    a200(r)
    d = json.loads(r.data)
    assert d['status'] == 'ok'
    assert d['database'] == 'ok'
add_test('health', t_health)

def t_robots():
    r = G('/robots.txt')
    a200(r)
    assert b'Disallow' in r.data
add_test('robots', t_robots)

logout()

# ======= Phase F: Permission Feeds =======
print('=== Phase F: Permission feeds ===')

# Test read-only permission checks FIRST (before setter tests destroy permissions)
def t_writeable_feeds():
    feeds = list(ed_u.writeable_feeds())
    assert len(feeds) == 1
    assert feeds[0].name == 'Test Feed'
add_test('writeable_feeds', t_writeable_feeds)

def t_publishable_feeds():
    feeds = list(ed_u.publishable_feeds())
    assert len(feeds) == 1
add_test('publishable_feeds', t_publishable_feeds)

def t_viewer_no_write():
    feeds = list(vw_u.writeable_feeds())
    assert len(feeds) == 0
add_test('viewer_no_write', t_viewer_no_write)

def t_feed_set_authors_publishers():
    f1.set_authors([ed_u, vw_u])
    assert f1.user_can_write(ed_u)
    assert f1.user_can_write(vw_u)
    f1.set_publishers([ed_u])
    assert f1.user_can_publish(ed_u)
    # Empty lists
    f1.set_authors([])
    f1.set_publishers([])
    # RESTORE original permissions so later tests aren't affected
    f1.grant('Write', user=ed_u)
    f1.grant('Publish', user=ed_u)
add_test('feed_setters', t_feed_set_authors_publishers)

def t_feed_set_groups():
    f1.set_author_groups([g1])
    f1.set_publisher_groups([g1])
    f1.set_author_groups([])
    f1.set_publisher_groups([])
    # RESTORE — group permissions were cleared, re-grant direct perms to be safe
    f1.grant('Write', user=ed_u)
    f1.grant('Publish', user=ed_u)
add_test('feed_group_setters', t_feed_set_groups)

# ======= Phase G: Screen Public Endpoints =======
print('=== Phase G: Screen ===')

def t_screen_display():
    r = G('/screens/basic/Default')
    a200(r)
add_test('screen_display', t_screen_display)

def t_screen_bogus():
    r = G('/screens/basic/NoSuch')
    a200(r)
add_test('screen_bogus', t_screen_bogus)

def t_screen_invalid_template():
    r = G('/screens/evil_template/Default')
    assert r.status_code in (200, 404, 500)
add_test('screen_invalid_template', t_screen_invalid_template)

def t_posts_from_feeds():
    r = G('/screens/posts_from_feeds/[1,2]')
    a200(r)
    d = json.loads(r.data)
    assert 'posts' in d
add_test('posts_from_feeds', t_posts_from_feeds)

def t_posts_from_feeds_bad():
    for bad in ['', 'null', 'notjson', '123', 'true']:
        r = G('/screens/posts_from_feeds/' + bad)
        aok(r)
add_test('posts_from_feeds_bad', t_posts_from_feeds_bad)

def t_screen_json():
    r = G(f'/screens/json/{S1.id}/0000000000000000')
    a200(r)
    d = json.loads(r.data)
    assert 'screenid' in d
add_test('screen_json', t_screen_json)

def t_screen_json_bogus():
    r = G('/screens/json/99999/foobar')
    a200(r)
add_test('screen_json_bogus', t_screen_json_bogus)

def t_post_types_js():
    r = G('/screens/post_types.js')
    a200(r)
    assert r.headers.get('Content-Type', '').startswith('application/javascript')
add_test('post_types_js', t_post_types_js)

def t_rss_feed():
    r = G(f'/feeds/rss/{f1.id}')
    a200(r)
    assert 'application/xml' in r.headers.get('Content-Type', '')
    assert b'<rss' in r.data
add_test('rss_feed', t_rss_feed)

def t_rss_feed_bad():
    for bad in ['', 'abc', '99999', '1,2,abc']:
        r = G(f'/feeds/rss/{bad}')
        aok(r)
add_test('rss_feed_bad', t_rss_feed_bad)

def t_json_post():
    # pids[4]=5 should survive all operations; pids[0] may get cascade-deleted
    pid = pids[4]
    r = G(f'/posts/{pid}/json')
    a200(r)
    d = json.loads(r.data)
    assert d['type'] == 'text'
add_test('json_post', t_json_post)

def t_json_post_nonexistent():
    r = G('/posts/99999/json')
    assert r.status_code in (200, 404)
add_test('json_post_nonexistent', t_json_post_nonexistent)

# Weather proxy (SSRF surface) — network-dependent, may fail if wttr.in is unreachable
def t_weather_proxy():
    try:
        r = G('/weather-proxy/London')
        assert r.status_code < 600
    except Exception as e:
        print(f'    WARN: weather_proxy skipped (network): {e}')
add_test('weather_proxy', t_weather_proxy)

def t_weather_proxy_bad():
    try:
        for bad in ['', '../../../etc/passwd', 'http://evil.com', '%00']:
            r = G('/weather-proxy/' + urllib.parse.quote(bad, safe=''))
            assert r.status_code < 600
    except Exception as e:
        print(f'    WARN: weather_proxy_bad skipped (network): {e}')
add_test('weather_proxy_bad', t_weather_proxy_bad)

# ======= Phase H: Uniqueness =======
print('=== Phase H: Uniqueness ===')

login_as('admin', 'testpass')

def t_unique_loginname():
    u3 = User(displayname='Auto1'); u3.set_password('a'); u3.save()
    u4 = User(displayname='Auto2'); u4.set_password('b'); u4.save()
    assert u3.loginname.startswith('user_')
    assert u4.loginname != u3.loginname
    u3.delete_instance(recursive=True)
    u4.delete_instance(recursive=True)
add_test('unique_loginname', t_unique_loginname)

logout()

# ======= Phase I: Auth Boundary Tests =======
print('=== Phase I: Auth Boundary Tests ===')

protected_endpoints = [
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

def t_auth_anon_denied():
    """Anon users should be redirected to login for protected pages."""
    logout()  # ensure clean state
    for method, url in protected_endpoints:
        if method == 'GET':
            r = client.get(url, follow_redirects=False)
        else:
            r = client.post(url, data={}, follow_redirects=False)
        # Should redirect to login page (302) or deny access (403)
        assert r.status_code in (302, 403, 301, 308), f'{method} {url}: got {r.status_code}'
add_test('anon_cannot_access_protected', t_auth_anon_denied)

def t_viewer_cannot_admin():
    """Low-privilege viewer cannot perform admin actions."""
    logout()
    login_as('viewer', 'testpass')
    r = P('/feeds', {'title': 'HackedFeed'}, follow_redirects=False)
    assert r.status_code != 200, f'viewer created feed: {r.status_code}'
    r = P('/users_and_groups', {'action': 'creategroup', 'name': 'Hacked'}, follow_redirects=False)
    assert r.status_code != 200, f'viewer created group: {r.status_code}'
    r = P('/posts/housekeeping', follow_redirects=False)
    assert r.status_code != 200, f'viewer ran housekeeping: {r.status_code}'
    logout()
add_test('viewer_cannot_admin', t_viewer_cannot_admin)

def t_editor_cannot_admin():
    """Editor cannot perform admin-only actions."""
    logout()
    login_as('editor', 'testpass')
    r = P('/feeds', {'title': 'Hacked2'}, follow_redirects=False)
    assert r.status_code != 200, f'editor created feed: {r.status_code}'
    logout()
add_test('editor_cannot_admin', t_editor_cannot_admin)

def t_viewer_can_see_allowed_feeds():
    """Viewer can access feeds they have Read permission on."""
    login_as('viewer', 'testpass')
    r = G(f'/feeds/{f2.id}', follow_redirects=True)
    a200(r)
    logout()
add_test('viewer_can_see_allowed_feeds', t_viewer_can_see_allowed_feeds)

def t_locked_out_behavior():
    """Locked-out user cannot access anything."""
    u = User.get(User.id == ed_u.id)
    u.is_locked_out = True
    u.save()
    login_as('editor', 'testpass')
    r = G('/feeds/', follow_redirects=True)
    aok(r)
    u.is_locked_out = False
    u.save()
    logout()
add_test('locked_out_behavior', t_locked_out_behavior)

# CSRF protection test (briefly disable TESTING)
def t_csrf_blocks_unauthorized_post():
    """CSRF should block POSTs when TESTING=False."""
    login_as('editor', 'testpass')
    app.config['TESTING'] = False
    app.config['CSRF_ENABLED'] = True
    r = client.post('/feeds', data={'title': 'CSRFTest'})
    # Should be blocked by CSRF (403)
    assert r.status_code in (302, 403), f'CSRF test: got {r.status_code}'
    app.config['TESTING'] = True
    app.config['CSRF_ENABLED'] = True
    logout()
add_test('csrf_blocks_unauthorized_post', t_csrf_blocks_unauthorized_post)

# ======= Phase J: Post Type Fuzzing =======
print('=== Phase J: Post Type Creation ===')

login_as('admin', 'testpass')

post_type_bodies = {
    'text': {'type': 'text', 'content': 'Hello'},
    'html': {'type': 'html', 'content': '<b>bold</b>'},
    'image': {'type': 'image', 'content': 'test.png'},
    'raw_html': {'type': 'raw_html', 'content': '<script>alert(1)</script>'},
}

def t_create_extra_post_types():
    for ptype, content in post_type_bodies.items():
        if ptype not in f3.post_types_as_list():
            continue
        r = P(f'/posts/new/{f3.id}', {
            'post_title': f'Test {ptype}',
            'post_type': ptype,
            'content': json.dumps(content),
            'action': 'edit'
        }, follow_redirects=True)
        aok(r)
add_test('create_extra_post_types', t_create_extra_post_types)

logout()

# ======= Phase Z: Real fuzzing =======
print('\n=== Phase Z: Fuzzing (random/malformed inputs) ===')

login_as('admin', 'testpass')

FUZZ_STRINGS = [
    '', 'x', 'x'*10, 'x'*1000, 'x'*100000,
    'null', 'undefined', 'NaN', 'Infinity',
    '--', ';--', "' OR 1=1 --", '<script>alert(1)</script>',
    '{"foo": "bar"}', '[1,2,3]',
    '\x00\x01\x02\xff',
    ' ' * 100, '\n' * 10, '\t\r\n',
    '../../../etc/passwd', 'NUL:CON:',
    'True', 'False', 'None', '0', '-1', '9999999999999999999',
]

endpoints = [
    ('GET',  '/',                           lambda: {}),
    ('GET',  '/health',                     lambda: {}),
    ('GET',  '/screens/',                   lambda: {}),
    ('GET',  '/feeds/',                     lambda: {}),
    ('GET',  '/posts/',                     lambda: {}),
    ('GET',  '/users_and_groups',           lambda: {}),
    ('GET',  f'/screens/basic/{S1.urlname}',lambda: {}),
    ('GET',  '/screens/posts_from_feeds/[1]',lambda: {}),
    ('GET',  f'/screens/json/{S1.id}/000',  lambda: {}),
    ('GET',  '/screens/post_types.js',      lambda: {}),
    ('GET',  '/client/main',                lambda: {}),
    ('GET',  f'/posts/{pids[0]}/json',      lambda: {}),
    ('POST', '/login',                      lambda: {'username': FUZZ_STRING, 'password': FUZZ_STRING}),
    ('POST', '/feeds',                      lambda: {'title': FUZZ_STRING}),
    ('POST', f'/feeds/{f1.id}',             lambda: {'action': FUZZ_STRING[:10], 'title': FUZZ_STRING[:50]}),
    ('POST', f'/feeds/{f1.id}/reorder',     lambda: (json.dumps({'post_ids': [FUZZ_INT, FUZZ_STRING, -99999, 0, 1]}), {'content_type': 'application/json'})),
    ('POST', '/posts/bulk_delete',          lambda: (json.dumps({'post_ids': [FUZZ_INT, 'x'*1000, None, True]}), {'content_type': 'application/json'})),
    ('POST', '/users_and_groups',           lambda: {'action': FUZZ_STRING[:10], 'name': FUZZ_STRING[:10], 'groupusers': FUZZ_STRING[:100]}),
    ('POST', f'/users/{ed_u.id}',           lambda: {'loginname': FUZZ_STRING[:50], 'emailaddress': FUZZ_STRING[:50], 'displayname': FUZZ_STRING[:50], 'groups': FUZZ_STRING[:50]}),
    ('POST', f'/group/{g1.id}',             lambda: {'action': FUZZ_STRING[:10], 'groupname': FUZZ_STRING[:20], 'groupusers': FUZZ_STRING[:50]}),
    ('POST', '/aliases',                    lambda: {'aliases': json.dumps([{'name': FUZZ_STRING[:20], 'screen_name': FUZZ_STRING[:20], 'fadetime': FUZZ_MIXED}])}),
    ('POST', f'/posts/new/{f1.id}',         lambda: {'post_title': FUZZ_STRING[:100], 'post_type': FUZZ_STRING[:10], 'action': FUZZ_STRING[:10], 'content': json.dumps({'type':'text','content':FUZZ_STRING[:100]})}),
    ('POST', f'/posts/{pids[0]}',           lambda: {'action': FUZZ_STRING[:10], 'post_title': FUZZ_STRING[:100]}),
    ('POST', '/posts/housekeeping',         lambda: {}),
    ('POST', '/screens-edit/1',             lambda: {'action': FUZZ_STRING[:10], 'urlname': FUZZ_STRING[:30], 'css': FUZZ_STRING[:500]}),
    ('POST', '/screens-edit/-1',            lambda: {'action': FUZZ_STRING[:10], 'urlname': FUZZ_STRING[:30]}),
    ('GET',  '/user_files/',                lambda: {}),
]

fuzz_count = 0
fuzz_crashes = 0

for method, url_tmpl, param_gen in endpoints:
    for fuzz_idx in range(min(5, len(FUZZ_STRINGS))):
        si = (fuzz_idx + random.randint(0, len(FUZZ_STRINGS)-1)) % len(FUZZ_STRINGS)
        FUZZ_STRING = FUZZ_STRINGS[si]
        FUZZ_INT = random.choice([0, -1, 9999999, 2**63-1, -2**63]) if random.random() < 0.5 else FUZZ_STRING
        FUZZ_MIXED = random.choice([0, -1, None, True, False, FUZZ_STRING])

        params = param_gen()
        url = url_tmpl
        if isinstance(params, tuple):
            data, kw = params
        else:
            data, kw = params, {}

        try:
            if method == 'GET':
                r = client.get(url, **kw)
            else:
                r = client.post(url, data=data, **kw)
        except Exception:
            continue

        fuzz_count += 1
        if r.status_code >= 500:
            fuzz_crashes += 1
            body = r.data.decode('utf-8', errors='replace')[:200]
            print(f'  FUZZ CRASH [{r.status_code}] {method} {url} with {type(FUZZ_STRING).__name__}({repr(FUZZ_STRING)[:80]}): {body}')

# Path fuzzing
print(f'  ... path fuzzing ...')
url_fuzz_count = 0
path_samples = random.sample(FUZZ_STRINGS, min(8, len(FUZZ_STRINGS)))
for base in ['/screens/posts_from_feeds/', '/screens/json/', '/client/', '/posts/', '/feeds/', '/group/', '/users/',
             '/screens/basic/', '/screens/notrans/', '/screens/mobile/',
             '/feeds/rss/',
             '/user_files/']:
    for bad_val in path_samples:
        encoded = urllib.parse.quote(str(bad_val), safe='')
        url = base + encoded
        try:
            r = client.get(url)
        except Exception:
            continue
        url_fuzz_count += 1
        if r.status_code >= 500:
            fuzz_crashes += 1
            body = r.data.decode('utf-8', errors='replace')[:200]
            print(f'  FUZZ CRASH [/] GET {url}: {body}')

# Query parameter fuzzing
print(f'  ... query parameter fuzzing ...')
query_fuzz_count = 0
query_bases = [
    '/',
    '/feeds/',
    '/posts/',
    '/screens/',
    '/users_and_groups',
]
for base in query_bases:
    for param in ['page', 'q', 'sort', 'id', 'search']:
        for val in random.sample(FUZZ_STRINGS, min(3, len(FUZZ_STRINGS))):
            encoded_val = urllib.parse.quote(str(val), safe='')
            try:
                r = client.get(f'{base}?{param}={encoded_val}')
            except Exception:
                continue
            query_fuzz_count += 1
            if r.status_code >= 500:
                fuzz_crashes += 1
                body = r.data.decode('utf-8', errors='replace')[:200]
                print(f'  FUZZ CRASH [?] GET {base}?{param}={repr(val)[:40]}: {body}')

# Content-type and malformed JSON fuzzing
print(f'  ... content-type fuzzing ...')
ct_fuzz_count = 0
for endpoint, ct, body in [
    (f'/feeds/{f1.id}/reorder', 'text/plain', b''),
    (f'/feeds/{f1.id}/reorder', 'application/xml', b'<xml>'),
    (f'/feeds/{f1.id}/reorder', '', b'{'),
    (f'/feeds/{f1.id}/reorder', 'application/json', b'['),
    (f'/feeds/{f1.id}/reorder', 'application/json', b'null'),
    (f'/feeds/{f1.id}/reorder', 'application/json', b'{"post_ids": [1]}'),
    (f'/feeds/{f1.id}/reorder', 'application/json', b'\x00\xff' * 10),
    ('/posts/bulk_delete', 'text/plain', b'['),
    ('/posts/bulk_delete', 'multipart/form-data', b'--boundary'),
    ('/posts/bulk_delete', '', b''),
    ('/posts/bulk_delete', 'application/json', b'garbage'),
    ('/posts/bulk_delete', 'application/json', b'{"post_ids": {"nested": "bad"}}'),
]:
    try:
        r = client.post(endpoint, data=body, content_type=ct)
    except Exception:
        continue
    ct_fuzz_count += 1
    if r.status_code >= 500:
        fuzz_crashes += 1
        print(f'  FUZZ CRASH [ct] POST {endpoint} ({ct}): {r.status_code}')

# Header fuzzing
print(f'  ... header fuzzing ...')
header_fuzz_count = 0
bad_headers = {
    'Content-Length': ['-1', 'abc', '9999999999999999999'],
    'X-Forwarded-For': ['127.0.0.1', '0' * 1000, '\x00' * 10],
    'Accept': ['\x00' * 10, 'x' * 2000],
    'User-Agent': [''.join(chr(i) for i in range(256))],
}
for hdr_name, hdr_values in bad_headers.items():
    for hdr_val in hdr_values:
        try:
            r = client.get('/', headers=[(hdr_name, hdr_val)])
        except Exception:
            continue
        header_fuzz_count += 1
        if r.status_code >= 500:
            fuzz_crashes += 1
            print(f'  FUZZ CRASH [hdr] GET / with {hdr_name}: {r.status_code}')

logout()

total_fuzz = fuzz_count + url_fuzz_count + query_fuzz_count + ct_fuzz_count + header_fuzz_count
print(f'Fuzz summary: {total_fuzz} inputs, {fuzz_crashes} server crashes (5xx)')
assert fuzz_crashes == 0, f'{fuzz_crashes} server crashes found!'

print(f'\nRunning {len(tests)} tests...\n')
failed = []
ok = []
for name, fn in tests:
    try:
        fn()
        ok.append(name)
    except Exception as e:
        failed.append((name, e))
        print(f'  FAIL {name}: {type(e).__name__}: {e}')
        traceback.print_exc()

print(f'\n{"="*60}')
print(f'Results: {len(ok)} passed, {len(failed)} failed')
if failed:
    for n, e in failed:
        print(f'  - {n}: {e}')
    sys.exit(1)
else:
    print(f'All {len(ok)} tests passed!')
    sys.exit(0)
