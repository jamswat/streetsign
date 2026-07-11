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
#    ---------------------------------
"""
    streetsign_server.views.utils
    -----------------------------

    No actual views in here, only bits and pieces to make views more
    fun.
"""
from functools import wraps
import re
from urllib.parse import urlparse

from flask import request, flash, render_template, make_response
import streetsign_server.user_session as user_session

# lots of wrappers, don't need these:
# pylint: disable=missing-docstring

class PleaseRedirect(Exception):
    '''
    so redirects can be passed back to views from logic functions.
    >>> def view_blah(...):
            try:
                do_stuff()
            except app.PleaseRedirect as e:
                flash(str(e.msg))
                redirect(e.url)
    '''
    def __init__(self, url='index', msg='Something went wrong'):
        self.msg = msg
        self.url = url

# these are some quick functions for getting sanitized form items,
# later we should probably transition to WTForms, or similar. But these
# will do for now.

def getint(name, default, minimum=0, maximum=999999999, form=None):
    """ get an integer from the request.form, capped with min and max,
        and a default.  If its not a valid integer, return the default.  """

    form = form or request.form
    try:
        return min(max(int(form.get(name, default)), minimum), maximum)
    except Exception:
        return default

def getbool(name, default, form=None):
    """ get a bool from the request.form.  if it's not valid, return the
        default. """
    form = form or request.form
    try:
        val = form.get(name, default)
        return val in (True, 1, '1',
                       'true', 'True', 'TRUE',
                       'yes', 'Yes', 'YES',
                       'checked', 'Checked', 'CHECKED')
    except Exception:
        return default

# some getstr helper regexps:
STRIPSTR = re.compile(r'^(?:\W*)([\w].*?)(\W*)$')
DATESTR = re.compile(r'(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)')

def getstr(name, default, validate='(.*)', flags=0, form=None):
    """ get a string from request.form. if it's not there, then return the
        default. """
    form = form or request.form
    try:
        return re.search(validate, str(form[name]), flags).group(1)
    except AttributeError: # no matches
        return default
    except KeyError: # no key in form
        return default

def admin_only(*methods):
    '''
        decorator for views to restrict access to admin users only.
    '''
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if request.method in methods:
                try:
                    user = user_session.get_user()
                except user_session.NotLoggedIn:
                    flash('Sorry! You need to be logged in!')
                    return permission_denied('You must be logged in!')

                if not user or not user.is_admin:
                    flash('Sorry! You need to be an admin!')
                    return permission_denied('You must be an admin!')

            return f(*args, **kwargs)
        return wrapped
    return wrapper

def registered_users_only(*methods):
    '''
        decorator for views to restrict access to registered users only.
    '''
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if request.method in methods:
                try:
                    user = user_session.get_user()
                except user_session.NotLoggedIn:
                    flash('Sorry! You need to be logged in!')
                    return permission_denied('You must be logged in!')
                if not user:
                    flash('Sorry! You need to be logged in!')
                    return permission_denied('You must be logged in!')

            return f(*args, **kwargs)
        return wrapped
    return wrapper

def permission_denied(message="You don't have permission! Sorry!",
                      title="Permission Denied"):
    ''' return the error.html template, with a message, and the HTTP code '''
    return make_response(render_template('error.html',
                                         title=title,
                                         message=message), 403)

def not_found(message="Page Not Found", title="Not Found"):
    ''' return the error.html template, with a message, and the HTTP code '''
    return make_response(render_template('error.html',
                                         title=title,
                                         message=message), 404)


def safe_referrer(fallback='/'):
    ''' Return request.referrer only if it is same-origin with the current
        request, otherwise return the fallback.

        Prevents open-redirect attacks where an attacker crafts a page
        whose Referer header points to an external URL — if we blindly
        redirect to request.referrer after login, the user is bounced to
        an attacker-controlled site. '''
    referrer = request.referrer
    if not referrer:
        return fallback

    parsed = urlparse(referrer)

    # Protocol-relative URLs (//evil.com) are dangerous — treat as external.
    if not parsed.scheme:
        return fallback

    # Allow only the same host as the current request. netloc includes the
    # port, which is what we want — different ports are different origins.
    if parsed.netloc == request.host:
        return referrer

    return fallback
