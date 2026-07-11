# -*- coding: utf-8 -*-
#  StreetSign Digital Signage Project
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
#    -------------------------------
"""
---------------------------------------
streetsign_server.logic.feeds_and_posts
---------------------------------------

logic for feeds_and_posts views, separated out for clarity.

"""

from datetime import datetime
import os
import re
from os.path import join as pathjoin, isfile, isdir, realpath, splitext
from os import sep as ossep

from flask import flash, url_for, json, g

from streetsign_server.views.utils import PleaseRedirect, \
                                          getstr, getint, getbool, \
                                          DATESTR
from streetsign_server.models import Feed, Post, now

def try_to_set_feed(post, new_feed_id, user):
    ''' Is this user actually allowed to set the feed of this post to what
        the form is saying they want to?  If so, cool. Return that feed. '''

    try:
        if post.feed:
            oldfeedid = post.feed.id
        else:
            oldfeedid = False
    except Exception:
        oldfeedid = False

    if new_feed_id and new_feed_id != oldfeedid:
        # new or changed feed.
        try:
            feed = Feed.get(Feed.id == new_feed_id)
        except Feed.DoesNotExist as exc:
            raise PleaseRedirect(None,
                                 "Odd. You somehow tried to post "
                                 "to a non-existant feed. It didn't work.") from exc

        if feed.user_can_write(user):
            flash('Posted to ' + feed.name)
            return feed

        # This shouldn't happen very often - so don't worry about
        # losing post data.  If it's an issue, refactor so it's stored
        # but not written to the feed...
        raise PleaseRedirect(
            url_for('index'),
            "Sorry, you don't have permission to write to " + feed.name)

    return post.feed

def if_i_cant_write_then_i_quit(post, user):
    ''' checks if a post is editable by a user. If it isn't, for
        whatever reason, then raise an appropriate 'PleaseRedirect'
        exception. (reasons could be that it's in a feed we don't
        have write access to, or it's been published, and we don't
        have publish permission to that feed, so the post is now
        'locked' to us.) '''

    # if we don't have write permission, then this isn't our post!
    if not post.feed.user_can_write(user):

        raise PleaseRedirect(
            None,
            f"Sorry, this post is in feed '{post.feed.name}', which"
            " you don't have permission to post to."
            " Edit cancelled.")

    # if this post is already published, be careful about editing it!
    if post.published and not post.feed.user_can_publish(user):

        raise PleaseRedirect(
            None,
            f'Sorry, this post is published,'
            ' and you do not have permission to'
            f' edit published posts in "{post.feed.name}".')

    return True

def can_user_write_and_publish(user, post):
    ''' returns a tuple, expressing if 'user' has permission to
        write and publish a post. '''

    if not post.feed:
        if user.writeable_feeds():
            return True, False

    # there is a feed selected
    if post.feed and post.feed.user_can_write(user):
        if post.feed.user_can_publish(user):
            return True, True
        return True, False

    # default is secure:
    return False, False

def clean_date(in_text):
    ''' take some input text, and return a datetime, if possible. '''
    return datetime.strptime(in_text.split('.')[0], "%Y-%m-%d %H:%M:%S")

def post_form_intake(post, form, editor):
    ''' takes the values from 'form', passes the post contents to
        the editor 'receive' function, and adds all the values into
        the 'post' object.

        NOTE: this actually modifies the post it is sent!
    '''

    user_provided_title = form.get('post_title', '').strip()
    if user_provided_title:
        post.title = user_provided_title
    elif not post.title:
        post.title = None

    existing = post.content
    try:
        post.content = json.dumps(editor.receive(form))
    except Exception:
        if not existing:
            raise

    # If no title was provided, auto-generate one
    if not user_provided_title and not post.title:
        auto_title = None
        try:
            content_data = json.loads(post.content)
            filename = content_data.get('filename', '')
            if filename:
                auto_title = re.sub(r'^[0-9a-f\-]{36}', '', filename)
        except Exception:
            pass

        if not auto_title:
            date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            auto_title = f"{getattr(editor, '__NAME__', 'Post')} - {date_str}"

        post.title = auto_title

    post.status = 0 # any time a post is edited, remove it from archive.

    post.time_restrictions_show = \
        form.get('times_mode', 'do_not_show') == 'only_show'

    # Validate time_restrictions as JSON before storing so the field can
    # never hold an arbitrary attacker-supplied string that later gets
    # rendered into a <script> block in the post editor. A round-trip
    # through json.loads/json.dumps guarantees the stored value is valid
    # JSON; the template re-encodes it with |tojson when emitting.
    raw_restrictions = form.get('time_restrictions_json', '[]')
    try:
        post.time_restrictions = json.dumps(json.loads(raw_restrictions))
    except (ValueError, TypeError):
        post.time_restrictions = '[]'

    # Recurrence (day-of-week scheduling):
    recurrence_enabled = getbool('recurrence_enabled', False, form=form)
    recurrence_days = form.getlist('recurrence_days') if hasattr(form, 'getlist') \
                      else [d for d in form.get('recurrence_days', '').split(',')
                            if d.strip()]
    post.recurrence = json.dumps({
        'enabled': recurrence_enabled,
        'days': recurrence_days,
    })

    if getbool('permanent', False, form=form):
        post.display_time = 0
        post.active_end = '2099-12-31 23:59:59'
        post.active_start = \
            getstr('active_start', post.active_start, validate=DATESTR, form=form)
    else:
        post.display_time = \
            getint('displaytime', 8, minimum=2, maximum=100, form=form)
        post.active_start = \
            getstr('active_start', post.active_start, validate=DATESTR, form=form)
        post.active_end = \
            getstr('active_end', post.active_end, validate=DATESTR, form=form)

    fontsize = getint('post_fontsize', 0, minimum=0, form=form)
    if form.get('post_fontsize_mode', '') == 'custom' and fontsize > 0:
        post.fontsize = fontsize
    else:
        post.fontsize = 0

    post.write_date = now()

def delete_post_and_run_callback(post, typemodule):
    ''' before a post is actually deleted, check if there is a 'pre-delete'
        callback on this post type, and run that first.  This way, for uploaded
        images (for instance), the file can be deleted as well. '''

    try:
        typemodule.delete(json.loads(post.content))
    except AttributeError:
        pass
        # There's no callback for this posttype, which is fine.
        # most post types will store no external data, and so don't need
        # to do anything.
    except Exception as excp:
        flash(str(excp))

    return post.delete_instance()

def cleanup_orphaned_media_files():
    ''' Scan post_images/ and post_videos/ directories for files that have
        no corresponding Post record in the database, and remove them.
        Also removes orphaned thumbnails.
        Returns a dict with counts of removed files and thumbnails. '''

    user_dir = g.site_vars['user_dir']
    removed_files = 0
    removed_thumbs = 0

    # Build the set of known filenames from all image and video posts.
    # If ANY post's content can't be parsed we must NOT delete anything -
    # otherwise a single corrupt row would cause us to treat its (live)
    # backing file as an orphan and delete it. Fail safe instead.
    known_filenames = set()
    for post in Post.select().where(Post.type << ['image', 'video']):
        try:
            data = json.loads(post.content)
        except Exception:
            return {'removed_files': 0, 'removed_thumbs': 0,
                    'aborted': True,
                    'reason': f'Could not parse content of post {post.id}; '
                              'aborting cleanup to avoid deleting live files.'}
        filename = data.get('filename', '')
        if filename:
            known_filenames.add(filename)

    # Scan post_images/ directory:
    image_dir = pathjoin(user_dir, 'post_images')
    if isdir(image_dir):
        for f in os.listdir(image_dir):
            filepath = pathjoin(image_dir, f)
            if isfile(filepath) and f not in known_filenames:
                try:
                    os.remove(filepath)
                    removed_files += 1
                except OSError:
                    pass
                thumb_path = pathjoin(user_dir, '.thumbnails', 'post_images',
                                    splitext(f)[0] + '.png')
                thumb_base = realpath(pathjoin(user_dir, '.thumbnails'))
                if realpath(thumb_path).startswith(thumb_base + ossep) \
                        and isfile(thumb_path):
                    try:
                        os.remove(thumb_path)
                        removed_thumbs += 1
                    except OSError:
                        pass

    # Scan post_videos/ directory:
    video_dir = pathjoin(user_dir, 'post_videos')
    if isdir(video_dir):
        for f in os.listdir(video_dir):
            filepath = pathjoin(video_dir, f)
            if isfile(filepath) and f not in known_filenames:
                try:
                    os.remove(filepath)
                    removed_files += 1
                except OSError:
                    pass

    return {'removed_files': removed_files, 'removed_thumbs': removed_thumbs}
