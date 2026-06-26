#!.virtualenv/bin/python3

'''
A set of useful database bits and pieces for StreetSign.
To be merged with run.py into a simple manage.py (django-style) script.

'''
#pylint: disable=wildcard-import, no-member, unused-wildcard-import, unused-import

import json
from datetime import datetime

import streetsign_server  # noqa: F401  pylint: disable=unused-import

from streetsign_server.models import *

def _user_exists(name):
    ''' test if a user exists '''
    return User.select().where(User.loginname == name).exists()


def _published_post(**kwargs):
    ''' helper: create an already-published post. '''
    kwargs.setdefault('published', True)
    kwargs.setdefault('publish_date', datetime.now())
    Post(**kwargs).save()


def make():
    ''' Seed a fresh database with a sensible, immediately-usable default
        state: a few users and groups, feeds with proper permissions, some
        example posts, and a working two-zone demo screen.

        Safe to re-run: it skips anything that already exists. '''
    create_all()

    ############################
    # Users & groups.
    #
    # NOTE: these are *demo* credentials. The README and login screen tell
    # operators to change them before deploying. Passwords match the login
    # name to make them easy to remember in a fresh install.

    admins = Group.get_or_create(name='admins', defaults={'display': True})[0]
    editors = Group.get_or_create(name='editors', defaults={'display': True})[0]

    if not _user_exists('admin'):
        admin = User(loginname='admin', displayname='Administrator',
                     emailaddress='admin@localhost', is_admin=True)
        admin.set_password('admin')
        admin.save()
        admin.set_groups([admins.id])
    else:
        admin = User.get(User.loginname == 'admin')

    if not _user_exists('editor'):
        editor = User(loginname='editor', displayname='Content Editor',
                      emailaddress='editor@localhost', is_admin=False)
        editor.set_password('editor')
        editor.save()
        editor.set_groups([editors.id])
    else:
        editor = User.get(User.loginname == 'editor')

    if not _user_exists('viewer'):
        viewer = User(loginname='viewer', displayname='Read-only Viewer',
                      emailaddress='viewer@localhost', is_admin=False)
        viewer.set_password('viewer')
        viewer.save()
    else:
        viewer = User.get(User.loginname == 'viewer')

    #################################
    # Feeds + permissions.
    #
    # 'editors' group can write & publish everywhere; 'viewer' can only read.

    def make_feed(name, post_types):
        feed = Feed.get_or_create(
            name=name, defaults={'post_types': post_types})[0]
        feed.post_types = post_types
        feed.save()
        # editors group: full authoring + publishing.
        feed.grant('Write', group=editors)
        feed.grant('Publish', group=editors)
        # viewer user: read only.
        feed.grant('Read', user=viewer)
        return feed

    welcome = make_feed('Welcome', 'html, text')
    news = make_feed('News', 'html, text, image')
    announcements = make_feed('Announcements', 'html, text')

    #################################
    # Example posts (only if the feeds are empty).

    if welcome.posts.count() == 0:
        _published_post(
            type='html', title='Welcome to StreetSign', feed=welcome,
            author=admin, publisher=admin, display_time=12,
            content=json.dumps({
                'type': 'html',
                'owntextcolor': False,
                'color': '#ffffff',
                'content': '<h1>Welcome to StreetSign</h1>'
                           '<p>This is your new digital signage server. '
                           'Edit or delete this post from the control '
                           'panel.</p>'}))
        _published_post(
            type='html', title='Getting started', feed=welcome,
            author=admin, publisher=admin, display_time=12,
            content=json.dumps({
                'type': 'html',
                'owntextcolor': False,
                'color': '#ffffff',
                'content': '<h2>Getting started</h2>'
                           '<ul>'
                           '<li>Create <b>posts</b> and group them into '
                           '<b>feeds</b>.</li>'
                           '<li>Design a <b>screen</b> with zones, and point '
                           'each zone at a feed.</li>'
                           '<li>Open a screen URL on any browser to turn it '
                           'into a display.</li>'
                           '</ul>'}))

    if news.posts.count() == 0:
        _published_post(
            type='text', title='Sample news item', feed=news,
            author=admin, publisher=admin, display_time=10,
            content=json.dumps({
                'type': 'text',
                'content': 'This is a plain-text post. Plain text is '
                           'auto-scaled to fill its zone.'}))

    if announcements.posts.count() == 0:
        # A clock/date post using the live "magic variables".
        _published_post(
            type='html', title='Date & time', feed=announcements,
            author=admin, publisher=admin, display_time=8,
            content=json.dumps({
                'type': 'html',
                'owntextcolor': False,
                'color': '#ffffff',
                'content': '<div style="text-align: center">'
                           '<h1>%%TIME%%</h1>'
                           '<h3>%%DATE%%</h3>'
                           '</div>'}))

    #################################
    # A working default screen: a large main zone (welcome + news) and a
    # slimmer announcements bar across the bottom.

    if not Screen.select().where(Screen.urlname == 'Default').exists():
        main_zone = {
            'name': 'main',
            'top': '0%', 'left': '0%', 'right': '0%', 'bottom': '20%',
            'type': 'fade', 'color': '#ffffff', 'fontfamily': '',
            'fadetime': 500,
            'feeds': [welcome.id, news.id],
            'css': '',
        }
        ticker_zone = {
            'name': 'announcements',
            'top': '80%', 'left': '0%', 'right': '0%', 'bottom': '0%',
            'type': 'scroll', 'color': '#ffffff', 'fontfamily': '',
            'fadetime': 250,
            'feeds': [announcements.id],
            'css': '',
        }
        Screen(
            urlname='Default',
            settings=json.dumps({}),
            defaults=json.dumps({}),
            css='#zones { background-color: #1a1a2e; }',
            zones=json.dumps([main_zone, ticker_zone]),
        ).save()


def run_migrations():
    ''' run migrations, configured in models.py '''
    migrations()

if __name__ == '__main__':
    print('welcome to the database shell.')
    print('type:  make() to make default data')
    print('or init() to connect to the database for interative work.')
    print('dir() will show you the available functions and models')
    print('run_migrations() will run migrations on the database.')
