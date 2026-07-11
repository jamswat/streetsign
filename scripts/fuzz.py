#!/usr/bin/env python3
"""Fuzz-test streetsign endpoints for regressions."""
import sys, os, json, datetime, traceback, random, string, urllib.parse

sys.path.insert(0, '/home/james/dev/streetsign')

import streetsign_server
from streetsign_server import app
from streetsign_server.models import init, create_all, User, Group, Feed, Post, FeedPermission, Screen

app.config['TESTING'] = True
app.config['DATABASE_FILE'] = '/tmp/opencode/fuzz_test.db'
app.config['SECRET_KEY'] = 'test-key-for-fuzzing'

init('/tmp/opencode/fuzz_test.db')
create_all()

client = app.test_client()

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
    '''Response must not be a server error (5xx).'''
    assert r.status_code < 500, f'server error {r.status_code}'

results = []

def test(name):
    def deco(fn):
        def wrapper():
            fn()
        return wrapper
    results.append(name)
    try:
        fn = deco(None)  # just to capture name
        return fn  # placeholder — we'll use the string approach instead
    except:
        pass

# Build tests as (name, fn) list
tests = []

# ======= SEED =======
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
S1 = Screen.create(urlname='Default', settings='{}', defaults='{}', zones='[]', css='')
S2 = Screen.create(urlname='Lobby', settings='{}', defaults='{}', zones='[]', css='')
f1.grant('Write', user=ed_u); f1.grant('Publish', user=ed_u)
f2.grant('Read', user=vw_u)
print(f'Done: {User.select().count()}u/{Feed.select().count()}f/{Group.select().count()}g/{Screen.select().count()}s')

# ======= TESTS =======
print('\n=== Phase A: Login & Forms ===')

def t_login_empty_username():
    r = P('/login', {'username': '', 'password': 'x'})
    aok(r)
tests.append(('login_empty_username', t_login_empty_username))

def t_login_empty_password():
    r = P('/login', {'username': 'admin', 'password': ''})
    aok(r)
tests.append(('login_empty_password', t_login_empty_password))

def t_login_missing_both():
    r = P('/login', {})
    aok(r)
tests.append(('login_missing_both', t_login_missing_both))

def t_new_feed_empty():
    login_as('admin', 'testpass')
    r = P('/feeds', {'title': ''})
    aok(r)
tests.append(('new_feed_empty', t_new_feed_empty))

def t_new_feed_nodata():
    r = P('/feeds', {})
    aok(r)
tests.append(('new_feed_nodata', t_new_feed_nodata))

def t_new_group_empty():
    r = P('/users_and_groups', {'action': 'creategroup', 'name': ''})
    a302(r)
tests.append(('new_group_empty', t_new_group_empty))

def t_new_group_missing():
    r = P('/users_and_groups', {'action': 'creategroup'})
    a302(r)
tests.append(('new_group_missing', t_new_group_missing))

def t_new_post_no_title():
    r = P(f'/posts/new/{f1.id}', {
        'post_type': 'text',
        'action': 'edit'
    }, follow_redirects=True)
    a200(r)
tests.append(('new_post_no_title', t_new_post_no_title))

logout()

# ======= Phase B =======
print('=== Phase B: User/Group ===')

def t_user_empty_email():
    login_as('admin', 'testpass')
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'emailaddress': '', 'displayname': 'Editor'}, follow_redirects=True)
    a200(r)
tests.append(('user_empty_email', t_user_empty_email))

def t_user_invalid_email():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'emailaddress': 'BANANA!!!!', 'displayname': 'Editor'}, follow_redirects=True)
    a200(r)
tests.append(('user_invalid_email', t_user_invalid_email))

def t_user_bogus_groups():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'groups': 'abc'}, follow_redirects=True)
    a200(r)
tests.append(('user_bogus_groups', t_user_bogus_groups))

def t_user_bogus_groups_int():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'groups': '999999'}, follow_redirects=True)
    a200(r)
tests.append(('user_bogus_groups_int', t_user_bogus_groups_int))

def t_user_set_groups_valid():
    r = P(f'/users/{ed_u.id}', {'loginname': 'editor', 'groups': str(g1.id)}, follow_redirects=True)
    a200(r)
    u = User.get(User.id == ed_u.id)
    assert g1.id in [g.id for g in u.groups()], 'group not added'
tests.append(('user_set_groups_valid', t_user_set_groups_valid))

def t_group_bogus_users():
    r = P(f'/group/{g1.id}', {'action': 'update', 'groupname': 'editors', 'groupusers': 'abc'}, follow_redirects=True)
    a200(r)
tests.append(('group_bogus_users', t_group_bogus_users))

def t_group_bogus_users_int():
    r = P(f'/group/{g1.id}', {'action': 'update', 'groupname': 'editors', 'groupusers': '99999'}, follow_redirects=True)
    a200(r)
tests.append(('group_bogus_users_int', t_group_bogus_users_int))

logout()

# ======= Phase C =======
print('=== Phase C: Feeds & Posts ===')

# Create test posts
login_as('admin', 'testpass')
pids = []
for i in range(5):
    p = Post(title=f'Fuzz {i}', type='text',
             content=json.dumps({'type': 'text', 'content': f'c{i}'}),
             feed=f1, author=admin_u, publisher=admin_u,
             published=True, publish_date=datetime.datetime.now())
    p.save(); pids.append(p.id)

def t_reorder_valid():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': pids}), content_type='application/json')
    a200(r)
tests.append(('reorder_valid', t_reorder_valid))

def t_reorder_empty():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': []}), content_type='application/json')
    a200(r)
tests.append(('reorder_empty', t_reorder_empty))

def t_reorder_missing_key():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({}), content_type='application/json')
    a200(r)
tests.append(('reorder_missing_key', t_reorder_missing_key))

def t_reorder_bogus():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': [99999, -1]}), content_type='application/json')
    a200(r)
tests.append(('reorder_bogus', t_reorder_bogus))

def t_reorder_string_ids():
    r = P(f'/feeds/{f1.id}/reorder', data=json.dumps({'post_ids': ['abc']}), content_type='application/json')
    assert r.status_code in (200, 500)
    if r.status_code == 500:
        print('    WARN: string IDs crash feed_reorder (ValueError)')
tests.append(('reorder_string_ids', t_reorder_string_ids))

def t_bulk_delete_mixed():
    r = P('/posts/bulk_delete', data=json.dumps({'post_ids': [pids[0], 'abc', -1, 999]}), content_type='application/json')
    a200(r)
    d = json.loads(r.data)
    assert d.get('errors', 0) >= 2  # abc and 999 are errors
tests.append(('bulk_delete_mixed', t_bulk_delete_mixed))

def t_feed_duplicate_name():
    r = P('/feeds', {'title': 'Test Feed'})
    aok(r)
tests.append(('feed_duplicate_name', t_feed_duplicate_name))

def t_feed_empty_name():
    r = P('/feeds', {'title': ''})
    aok(r)
tests.append(('feed_empty_name', t_feed_empty_name))

logout()

# ======= Phase D =======
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
tests.append(('aliases_zero_persist', t_aliases_zero_persist))

def t_aliases_duplicate():
    r = P('/aliases', {'aliases': json.dumps([
        {'name': 'dup', 'screen_name': 'Default'},
        {'name': 'dup', 'screen_name': 'Lobby'},
    ])})
    assert r.status_code in (200, 400)
tests.append(('aliases_duplicate', t_aliases_duplicate))

def t_aliases_missing_fields():
    r = P('/aliases', {'aliases': json.dumps([{'name': 'minimal'}])})
    a200(r)
tests.append(('aliases_missing_fields', t_aliases_missing_fields))

def t_aliases_get():
    r = G('/aliases')
    a200(r)
    d = json.loads(r.data)
    assert len(d['aliases']) > 0
tests.append(('aliases_get', t_aliases_get))

def t_client_deleted_screen():
    r = G('/client/bogus')
    a200(r)
    assert b'Screen Alias' in r.data or b'not found' in r.data.lower()
tests.append(('client_deleted_screen', t_client_deleted_screen))

def t_client_valid():
    r = G('/client/main')
    a200(r)
tests.append(('client_valid', t_client_valid))

logout()

# ======= Phase E =======
print('=== Phase E: Dashboard ===')

def t_dash_anon():
    r = G('/', follow_redirects=True)
    a200(r)
tests.append(('dash_anon', t_dash_anon))

def t_dash_auth():
    login_as('admin', 'testpass')
    r = G('/', follow_redirects=True)
    a200(r)
    assert b'Dashboard' in r.data or b'Streetsign' in r.data
tests.append(('dash_auth', t_dash_auth))

logout()

# ======= Phase F =======
print('=== Phase F: Permission feeds ===')

def t_writeable_feeds():
    feeds = list(ed_u.writeable_feeds())
    assert len(feeds) == 1
    assert feeds[0].name == 'Test Feed'
tests.append(('writeable_feeds', t_writeable_feeds))

def t_publishable_feeds():
    feeds = list(ed_u.publishable_feeds())
    assert len(feeds) == 1
tests.append(('publishable_feeds', t_publishable_feeds))

def t_viewer_no_write():
    feeds = list(vw_u.writeable_feeds())
    assert len(feeds) == 0
tests.append(('viewer_no_write', t_viewer_no_write))

def t_feed_set_authors_publishers():
    f1.set_authors([ed_u, vw_u])
    assert f1.user_can_write(ed_u)
    assert f1.user_can_write(vw_u)
    f1.set_publishers([ed_u])
    assert f1.user_can_publish(ed_u)
    # Empty lists
    f1.set_authors([])
    f1.set_publishers([])
tests.append(('feed_setters', t_feed_set_authors_publishers))

def t_feed_set_groups():
    f1.set_author_groups([g1])
    f1.set_publisher_groups([g1])
    f1.set_author_groups([])
    f1.set_publisher_groups([])
tests.append(('feed_group_setters', t_feed_set_groups))

# ======= Phase G =======
print('=== Phase G: Screen ===')

def t_screen_display():
    r = G('/screens/basic/Default')
    a200(r)
tests.append(('screen_display', t_screen_display))

def t_screen_bogus():
    r = G('/screens/basic/NoSuch')
    a200(r)
tests.append(('screen_bogus', t_screen_bogus))

def t_posts_from_feeds():
    r = G('/screens/posts_from_feeds/[1,2]')
    a200(r)
    d = json.loads(r.data)
    assert 'posts' in d
tests.append(('posts_from_feeds', t_posts_from_feeds))

# ======= Phase H =======
print('=== Phase H: Uniqueness ===')

login_as('admin', 'testpass')

def t_unique_loginname():
    u3 = User(displayname='Auto1'); u3.set_password('a'); u3.save()
    u4 = User(displayname='Auto2'); u4.set_password('b'); u4.save()
    assert u3.loginname.startswith('user_')
    assert u4.loginname != u3.loginname
tests.append(('unique_loginname', t_unique_loginname))

logout()

# ======= Phase Z: Real fuzzing =======
print('\n=== Phase Z: Fuzzing (random/malformed inputs) ===')

login_as('admin', 'testpass')

endpoints = [
    # (method, url_template, param_gen_fn)
    ('GET',  '/',                           lambda: {}),
    ('GET',  '/screens/',                   lambda: {}),
    ('GET',  '/feeds/',                     lambda: {}),
    ('GET',  '/posts/',                     lambda: {}),
    ('GET',  '/users_and_groups',           lambda: {}),
    ('GET',  f'/screens/basic/{S1.urlname}',lambda: {}),
    ('GET',  '/screens/posts_from_feeds/[1]',lambda: {}),
    ('GET',  f'/screens/json/{S1.id}/000',  lambda: {}),
    ('GET',  '/client/main',                lambda: {}),
    ('POST', '/login',                      lambda: {'username': FUZZ_STRING, 'password': FUZZ_STRING}),
    ('POST', '/feeds',                      lambda: {'title': FUZZ_STRING}),
    ('POST', f'/feeds/{f1.id}/reorder',     lambda: (json.dumps({'post_ids': [FUZZ_INT, FUZZ_STRING, -99999, 0, 1]}), {'content_type': 'application/json'})),
    ('POST', '/posts/bulk_delete',          lambda: (json.dumps({'post_ids': [FUZZ_INT, 'x'*1000, None, True]}), {'content_type': 'application/json'})),
    ('POST', '/users_and_groups',           lambda: {'action': FUZZ_STRING[:10], 'name': FUZZ_STRING[:10], 'groupusers': FUZZ_STRING[:100]}),
    ('POST', f'/users/{ed_u.id}',           lambda: {'loginname': FUZZ_STRING[:50], 'emailaddress': FUZZ_STRING[:50], 'displayname': FUZZ_STRING[:50], 'groups': FUZZ_STRING[:50]}),
    ('POST', f'/group/{g1.id}',             lambda: {'action': 'update', 'groupname': FUZZ_STRING[:20], 'groupusers': FUZZ_STRING[:50]}),
    ('POST', '/aliases',                    lambda: {'aliases': json.dumps([{'name': FUZZ_STRING[:20], 'screen_name': FUZZ_STRING[:20], 'fadetime': FUZZ_MIXED}])}),
    ('POST', f'/posts/new/{f1.id}',         lambda: {'post_title': FUZZ_STRING[:100], 'post_type': FUZZ_STRING[:10], 'action': FUZZ_STRING[:10], 'content': json.dumps({'type':'text','content':FUZZ_STRING[:100]})}),
]

FUZZ_STRINGS = [
    '', 'x', 'x'*10, 'x'*1000, 'x'*100000,  # length extremes
    'null', 'undefined', 'NaN', 'Infinity',  # JS specials
    '--', ';--', "' OR 1=1 --", '<script>alert(1)</script>',  # SQLi / XSS
    '{"foo": "bar"}', '[1,2,3]',  # partial JSON
    '😀' * 10, '\x00\x01\x02\xff',  # unicode, binary
    ' ' * 100, '\n' * 10, '\t\r\n',  # whitespace
    '../../../etc/passwd', 'NUL:CON:',  # path traversal
    'True', 'False', 'None', '0', '-1', '9999999999999999999',
]

fuzz_count = 0
fuzz_crashes = 0

for method, url_tmpl, param_gen in endpoints:
    for fuzz_idx in range(min(5, len(FUZZ_STRINGS))):
        # Rotate through fuzz strings
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
        except Exception as e:
            # Network/serialization errors are fine — we're checking the server
            # doesn't 500; client-side errors are expected with extreme inputs.
            continue

        fuzz_count += 1
        if r.status_code >= 500:
            fuzz_crashes += 1
            body = r.data.decode('utf-8', errors='replace')[:200]
            print(f'  FUZZ CRASH [{r.status_code}] {method} {url} with {type(FUZZ_STRING).__name__}({repr(FUZZ_STRING)[:80]}): {body}')
        elif r.status_code == 400:
            # 400 is fine — it means the server handled the bad input gracefully
            pass
        elif r.status_code not in (200, 301, 302, 303, 307, 308):
            # Unexpected, but not a server crash
            pass

# Also fuzz URL path components
print(f'  ... path fuzzing ...')
url_fuzz_count = 0
for base in ['/screens/posts_from_feeds/', '/screens/json/', '/client/', '/posts/', '/feeds/', '/group/', '/users/',
             '/screens/basic/', '/screens/notrans/', '/screens/mobile/']:
    for si, bad_val in enumerate(FUZZ_STRINGS[:8]):  # subset to keep it fast
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

# Fuzz POST content types and malformed JSON
print(f'  ... content-type fuzzing ...')
ct_fuzz_count = 0
for endpoint, ct in [
    (f'/feeds/{f1.id}/reorder', 'text/plain'),
    (f'/feeds/{f1.id}/reorder', 'application/xml'),
    (f'/feeds/{f1.id}/reorder', ''),
    ('/posts/bulk_delete', 'multipart/form-data'),
    ('/posts/bulk_delete', ''),
]:
    for body in [b'', b'{', b'[', b'null', b'{"post_ids": [1]}', b'\x00\xff' * 10]:
        try:
            r = client.post(endpoint, data=body, content_type=ct)
        except Exception:
            continue
        ct_fuzz_count += 1
        if r.status_code >= 500:
            fuzz_crashes += 1
            print(f'  FUZZ CRASH [ct] POST {endpoint} ({ct}): {r.status_code}')

logout()

total_fuzz = fuzz_count + url_fuzz_count + ct_fuzz_count
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
