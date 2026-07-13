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

from uuid import uuid4
from hmac import compare_digest

from flask import render_template, g, Response, url_for, request, session, \
                   jsonify
from markupsafe import Markup

from urllib.parse import quote as url_quote
import urllib.request
import urllib.error

##########################
# views submodules:
import streetsign_server.views.users_and_auth
import streetsign_server.views.feeds_and_posts
import streetsign_server.views.user_files
import streetsign_server.views.screens
from streetsign_server import user_session

# pylint: disable=singleton-comparison,no-value-for-parameter

# set up the app
from streetsign_server import app
from streetsign_server.models import DB, ALL_MODELS, \
     Post, Screen, Feed, User, config_var, now

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
            'screendisplay', 'screens_posts_from_feeds', 'screen_json',
            'post_types_js', 'json_post', 'client_alias', 'robots_txt',
        ):
            return

        form_token = request.form.get('_csrf_token', '') or \
                     request.headers.get('X-CSRF-Token', '')
        if not compare_digest(str(form_token), str(session['_csrf_token'])):
            return Response('CSRF validation failed', status=403)


@app.context_processor
def inject_csrf():
    """Inject CSRF token into all templates."""
    return {"csrf_token": session.get('_csrf_token', '')}


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
                           .where((Post.published == False) &
                                  (Post.feed << publishable_feeds))

    screens = Screen.select()
    aliases = config_var('screens.aliases', [])

    # Summary stats for dashboard cards
    total_screens = Screen.select().count()
    total_feeds = Feed.select().count()
    active_posts_count = Post.select().where(
        (Post.published == True) &
        (Post.active_start <= now()) &
        (Post.active_end >= now())
    ).count()

    recent_posts = Post.select().where(Post.published == True)\
                       .order_by(Post.write_date.desc()).limit(5)

    screens_by_name = {s.urlname: s for s in screens}
    for alias in aliases:
        alias['screen'] = screens_by_name.get(alias.get('screen_name'))

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
                           show_all=request.args.get('show_all', False),
                           total_screens=total_screens,
                           total_feeds=total_feeds,
                           active_posts_count=active_posts_count,
                           recent_posts=recent_posts,
                           breadcrumbs=[('Dashboard', None)])

@app.route('/robots.txt')
def robots_txt():
    ''' block all well-behaved search engines. '''
    return Response('User-agent: *\nDisallow: /', mimetype='text/plain')


@app.route('/health')
def health():
    ''' Lightweight liveness probe. Reports OK only if the database is
        reachable and a trivial query succeeds.

        Intended for Docker HEALTHCHECK, load-balancer probes, and
        monitoring systems. Does not require authentication. '''
    try:
        DB.execute_sql('SELECT 1').fetchone()
    except Exception as exc:  # pylint: disable=broad-except
        app.logger.exception('health check failed: %s', exc)
        return jsonify(status='error',
                        database='unreachable'), 503
    return jsonify(status='ok', database='ok')


@app.route('/weather-proxy/<path:query>')
def weather_proxy(query):
    ''' Proxy requests to wttr.in to avoid CORS/CSP issues. '''
    url = f'https://wttr.in/{url_quote(query)}?format=j1'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; StreetSign/2.0)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        return Response(data, mimetype='application/json')
    except urllib.error.HTTPError as e:
        return jsonify(error=f'wttr.in returned HTTP {e.code}'), 502
    except Exception as e:
        return jsonify(error=f'Failed to fetch weather: {e}'), 502


# Expected Error Handlers:

@app.errorhandler(user_session.NotLoggedIn)
def not_logged_in(_err):
    ''' Not Logged In handler '''
    return render_template('error.html',
                          title='Permission Denied',
                          message="You're not logged in!"), 403
