# -*- coding: utf-8 -*-
# StreetSign Digital Signage Project
#     (C) Copyright 2013 Daniel Fairhead
#
#    StreetSign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    StreetSign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with StreetSign.  If not, see <http://www.gnu.org/licenses/>.
#
#    ---------------------------
'''
    streetsign_server.views
    -----------------------

    brings in all the main views from the other files.

'''

from flask import render_template, g, Response, url_for, request, session
from uuid import uuid4
from markupsafe import Markup
import datetime

##########################
# views submodules:
import streetsign_server.views.users_and_auth
import streetsign_server.views.feeds_and_posts
import streetsign_server.views.user_files
import streetsign_server.views.screens
import streetsign_server.user_session as user_session

# set up the app
from streetsign_server import app
from streetsign_server.models import DB, ALL_MODELS, \
     Post, Screen, Feed, User, config_var

######################################################################
# Basic App stuff:

@app.before_request
def before_the_action():
    ''' load some variables in for template etc to use '''

    g.site_vars = app.config.get('SITE_VARS')

    if '_csrf_token' not in session:
        session['_csrf_token'] = str(uuid4())

    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        if app.config.get('TESTING') or not app.config.get('CSRF_ENABLED', True):
            return
        if request.endpoint in (
            'login', 'logout',
            'screendisplay', 'screens_posts_from_feeds', 'screen_json',
            'post_types_js', 'posts_housekeeping', 'json_post',
            'external_data_source_run', 'external_data_sources_update_all',
            'external_source_test',
            'save_aliases', 'client_alias', 'robots_txt',
        ):
            return

        form_token = request.form.get('_csrf_token', '')
        if form_token != session['_csrf_token']:
            return Response('CSRF validation failed', status=403)


@app.context_processor
def inject_csrf():
    return dict(csrf_token=session.get('_csrf_token', ''))


@app.route('/')
@app.route('/index.html')
def index():
    ''' main front page / dashboard / index. '''
    try:
        user = user_session.get_user()
    except user_session.NotLoggedIn:
        user = User()

    if not user:
        user = User()


    publishable_feeds = user.publishable_feeds()


    posts_to_publish = Post.select()\
                           .where((Post.published is False) &
                                  (Post.feed << publishable_feeds))

    screens = Screen.select()
    aliases = config_var('screens.aliases', [])

    # Summary stats for dashboard cards
    total_screens = Screen.select().count()
    total_feeds = Feed.select().count()
    total_posts = Post.select().count()
    unpublished_posts = Post.select().where(Post.published == False).count()
    active_posts_count = Post.select().where(
        (Post.published == True) &
        (Post.active_start <= datetime.datetime.now()) &
        (Post.active_end >= datetime.datetime.now())
    ).count()

    recent_posts = Post.select().where(Post.published == True)\
                       .order_by(Post.write_date.desc()).limit(5)

    for alias in aliases:
        for screen in screens:
            if screen.urlname == alias['screen_name']:
                alias['screen'] = screen
                break
        else:
            alias['screen'] = None

    return render_template('dashboard.html',
                           aliases=aliases,
                           feeds=Feed.select(),
                           publishable_feeds=publishable_feeds,
                           posts=Post.select().where(Post.author == user)\
                                     .order_by(Post.write_date.desc())\
                                     .limit(15),
                           posts_to_publish=posts_to_publish,
                           screens=screens,
                           user=user,
                           total_screens=total_screens,
                           total_feeds=total_feeds,
                           total_posts=total_posts,
                           unpublished_posts=unpublished_posts,
                           active_posts_count=active_posts_count,
                           recent_posts=recent_posts,
                           breadcrumbs=[('Dashboard', None)])

@app.route('/robots.txt')
def robots_txt():
    ''' block all well-behaved search engines. '''
    return Response('User-agent: *\nDisallow: /', mimetype='text/plain')


# Expected Error Handlers:

@app.errorhandler(user_session.NotLoggedIn)
def not_logged_in(err):
    ''' Not Logged In handler '''
    # TODO: nicer looking.
    return f'''<!doctype html>
    <body><h1>StreetSign</h1>
    <h2>Permission Denied</h2>
    You\'re not logged in!
    <a href="{url_for("index")}">Return to StreetSign</a>''', 403
