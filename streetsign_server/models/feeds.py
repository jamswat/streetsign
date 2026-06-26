# -*- coding: utf-8 -*-
#  StreetSign Digital Signage Project
#     (C) Copyright 2013-2015 Daniel Fairhead
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
'''
===============================================
streetsign_server.models.feeds
===============================================

Feed, FeedPermission, Post, and ExternalSource ORM models.

The singleton-comparison warnings (x == True) throughout this module are
correct Peewee query expressions — they generate SQL WHERE clauses. Changing
them to 'is True' would break queries. The no-member warnings on .posts
(backref) and .split() (CharField) are Peewee metaprogramming invisible to
static analysis.

'''

# pylint: disable=singleton-comparison,no-member


import sqlite3
from datetime import datetime, timedelta

from flask import url_for
from markupsafe import Markup
from peewee import * # pylint: disable=wildcard-import,unused-wildcard-import
import bleach

from .base import DBModel, now, safe_json_load, eval_datetime_formula, PermissionDenied
from .users import User, Group, UserGroup


class Feed(DBModel):
    ''' A Feed is kind of like a collection, or category of posts.
        Different 'zones' on screen outputs will subscribe to these Feeds. '''

    #: the name of the feed.
    name = CharField(default='New Feed')

    #: which types of posts are allowed in this feed (comma,separated)?
    post_types = CharField(default='')

    def __repr__(self):
        return '<Feed:' + self.name + '>'

    def post_count(self, published=True, expired=False):
        ''' how many posts in this feed? '''
        q = self.posts
        if published:
            q = q.where(Post.published == True)
        if not expired:
            q = q.where(Post.active_end > now())
        return q.count()

    def post_types_as_list(self):
        ''' return a list of post types, from the single field '''
        return [i.strip() for i in self.post_types.split(',')]

    # Yes, I like comprehensions.
    def authors(self):
        ''' return all users with write permission '''
        return [p.user for p in self.permissions
                if p.write == True and p.user]

    def publishers(self):
        ''' return all users with publishing permission '''
        return [p.user for p in self.permissions
                if p.publish == True and p.user]

    def author_groups(self):
        ''' return all groups with write permission '''
        return [p.group for p in self.permissions
                if p.write == True and p.group]

    def publisher_groups(self):
        ''' return all groups with publishing permission '''
        return [p.group for p in self.permissions
                if p.publish == True and p.group]

    def user_can_read(self, user):
        ''' Checks read permission for a feed.  Not really used, as yet. '''
        if user.is_admin:
            return True

        if user.is_locked_out:
            return False

        # check for user-level read permission:
        if self.permissions.where((FeedPermission.user == user)
                                  &(FeedPermission.read == True)).exists():
            return True

        # check for group-level read permission:
        if (self.permissions.join(Group)
                            .join(UserGroup)
                            .where((UserGroup.user == user)
                                  &(FeedPermission.read == True)).exists()):
            return True

        # oh well! no permission!
        return False

    def user_can_write(self, user):
        ''' Checks write permission.  (Admins get automatically) '''
        if not user:
            return False

        if user.is_admin:
            return True

        if user.is_locked_out:
            return False

        # check for user-level read permission:
        if self.permissions.where((FeedPermission.user == user) &
                                  (FeedPermission.write == True)).exists():
            return True

        # check for group-level read permission:
        if (self.permissions.join(Group)
                            .join(UserGroup)
                            .where((UserGroup.user == user) &
                                   (FeedPermission.write == True)).exists()):
            return True

        # oh well! no permission!
        return False

    def user_can_publish(self, user):
        ''' Checks publish permission. (Admins get automatically) '''
        if not user:
            return False

        if user.is_admin:
            return True

        if user.is_locked_out:
            return False

        # check for user-level read permission:
        if self.permissions.where((FeedPermission.user == user) &
                                  (FeedPermission.publish == True)).exists():
            return True

        # check for group-level read permission:
        if (self.permissions.join(Group)
                            .join(UserGroup)
                            .where((UserGroup.user == user) &
                                   (FeedPermission.publish == True)).exists()):
            return True

        # oh well! no permission!
        return False

    def grant(self, permission, user=None, group=None):
        ''' Give either a user or group permission
            (either 'Read','Write' or 'Publish') on this Feed. '''

        # one of them *must* be selected...
        assert (user, group) != (None, None)
        assert (user and group) is None
        assert permission in ('Read', 'Write', 'Publish')
        # first get previous permission, if there is one.

        if permission == 'Read':
            p = FeedPermission.read
        elif permission == 'Write':
            p = FeedPermission.write
        elif permission == 'Publish':
            p = FeedPermission.publish
        else:
            raise ValueError('Invalid permission.'
                            ' Must be Read,Write, or Publish')

        try:
            if user:
                perm = FeedPermission.get((FeedPermission.feed == self)
                                         &(FeedPermission.user == user)
                                         &(p == True))
            elif group:
                perm = FeedPermission.get((FeedPermission.feed == self)
                                         &(FeedPermission.group == group)
                                         &(p == True))
            else:
                raise ValueError('You must specify either a user or a group!')
        except FeedPermission.DoesNotExist:
            perm = FeedPermission(feed=self, user=user, group=group)

        assert perm.user or perm.group

        perm.read = permission == 'Read'
        perm.write = permission == 'Write'
        perm.publish = permission == 'Publish'

        # if we try and grant permission *before* this is saved, it will
        # fail. So cascade the saves!
        try:
            perm.save()
        except sqlite3.IntegrityError:
            self.save()
            perm.feed = self
            perm.save()

    # and some convenience functions:
    def set_authors(self, authorlist):
        ''' set the complete authorlist. deletes previous set '''

        # delete old permissions first.
        FeedPermission.delete().where((FeedPermission.feed == self)
                                     &(FeedPermission.write == True)
                                     &(FeedPermission.user)).execute()
        for a in authorlist:
            assert isinstance(a, User)
            self.grant('Write', user=a)

    def set_publishers(self, publisherlist):
        ''' set the complete publisherlist. deletes previous set '''
        # delete old permissions first.
        FeedPermission.delete().where((FeedPermission.feed == self)
                                     &(FeedPermission.publish == True)
                                     &(FeedPermission.user)).execute()

        for p in publisherlist:
            assert isinstance(p, User)
            self.grant('Publish', user=p)

    def set_author_groups(self, authorlist):
        ''' set the complete author_groups list. deletes previous set '''

        # delete old permissions first.
        FeedPermission.delete().where((FeedPermission.feed == self)
                                     &(FeedPermission.write == True)
                                     &(FeedPermission.group)).execute()
        for a in authorlist:
            assert isinstance(a, Group)
            self.grant('Write', group=a)

    def set_publisher_groups(self, publisherlist):
        ''' set the complete publisher_groups list. deletes previous set '''
        # delete old permissions first.
        FeedPermission.delete().where((FeedPermission.feed == self)
                                     &(FeedPermission.publish == True)
                                     &(FeedPermission.group)).execute()

        for p in publisherlist:
            assert isinstance(p, Group)
            self.grant('Publish', group=p)

class FeedPermission(DBModel):
    ''' Essentially a cross-reference table, but with specified permissions. '''

    feed = ForeignKeyField(Feed, backref='permissions')

    user = ForeignKeyField(User, null=True)
    # OR...
    group = ForeignKeyField(Group, null=True)

    read = BooleanField(default=True)
    write = BooleanField(default=False)
    publish = BooleanField(default=False)

class Post(DBModel):
    ''' The actual main point of this whole thing.  The contents that get
        displayed.  This object/row/thing hands off all the actual editing
        of, displaying of, and validating of the contents to a post type
        module.  It's stored in the database as JSON.  This means new types
        of post can be added quite easily later, without changing the
        schema. '''

    title = TextField()  #: used to easily identify the post
    type = TextField() #: used to load the content-type module for this post
    content = TextField() #: JSON data sent to the content-type module
    fontsize = IntegerField(null=True)
    feed = ForeignKeyField(Feed, backref='posts') #: which feed

    author = ForeignKeyField(User, backref='posts') #: who wrote it?

    write_date = DateTimeField(default=now) #: when was it written?

    #publisher info:
    published = BooleanField(default=False) #: is this post published?
    publish_date = DateTimeField(null=True) #: when was it published?
    #: who published it?
    publisher = ForeignKeyField(User, backref='published_posts', null=True)

    # Should it actually be displayed?
    status = IntegerField(default=0) #: can be 0:active/1:finished/2:archived.
    status_options = {
        0: 'active',
        1: 'finished',
        2: 'archived'
        }

    # When should the feed actually be shown:
    active_start = DateTimeField(default=now) #: lifetime start
    active_end = DateTimeField(default=lambda: now() + \
                                               timedelta(weeks=1)) #: end

    #: Time restrictions don't need to be cross queried, and honestly
    #: are easier just left in javascript/JSON land:
    #: are these restrictions "Only show during these times" or
    #: "Do not show during these times" ?
    time_restrictions_show = BooleanField(default=False)

    #: and the actual restrictions:
    time_restrictions = TextField(default='[]')
    # {"start_time", "end_time", "note"}

    #: For how long should it be displayed?
    display_time = IntegerField(default=8)

    def __repr__(self):
        return f'<Post:{self.type}:{self.content[0:22]}>'

    def repr(self):
        ''' This is actually used by the back-end to display different
            'thumbnails' of posts.  If you want to show HTML (careful!!!!!!!!)
            then wrap it in Markup(), so jinja2 doesn't escape it. '''

        # TODO: split this out to the various post_type modules, and cache it.
        try:
            content = safe_json_load(self.content, {'content':'None'})['content']
        except KeyError:
            content = "N/A"

        if self.type == 'image':
            return Markup(
                f'<img src="{url_for("thumbnail", filename="post_images/"+content)}"'
                f' alt="{content}" />')
        return bleach.clean(content, tags=[], strip=True)[0:15] + '...(' + \
                self.type + ')'

    def dict_repr(self):
        ''' must give all info, for use on screens, etc. '''
        return (
            {'id': self.id,
             'title': self.title,
             'type': self.type,
             'content': safe_json_load(self.content, {}),
             'fontsize': self.fontsize,
             'time_restrictions': safe_json_load(self.time_restrictions, []),
             'time_restrictions_show': self.time_restrictions_show,
             'display_time': self.display_time * 1000, # in milliseconds
             'changed': self.write_date
            })

    def active_status(self):
        ''' is this post active now, in the future, or the past?
            (returns a string 'now'/'future'/'past') '''

        time_now = now()
        try:
            if not (self.active_start and self.active_end):
                return 'future'
            if self.active_start > time_now:
                return 'future'
            if self.active_end < time_now:
                return 'past'
            return 'now'
        except TypeError:
            # SQLite doesn't really do types, so this can happen.
            return 'now'

    def publish(self, user, state=True):
        ''' set the published status, published & date of this post.
            use state=False to unpublish '''
        if self.feed.user_can_publish(user):
            self.published = state
            self.publisher = user if state else None
            self.publish_date = now() if state else None
            self.save()
            return True
        raise PermissionDenied("You don't have permission to publish"
                               " posts on this feed.")

    def save(self, *vargs, **kwargs):
        ''' Save the state of the object to the database, updating
            the 'write_date' time along the way. '''

        self.write_date = now()
        return super().save(*vargs, **kwargs)



class ExternalSource(DBModel):
    ''' How do we pull data in from external sources? '''

    #: name, displayed in the interface
    name = CharField()

    #: source types are loaded in later, the same as post types.
    type = CharField()

    #: how often to check for new data at the source...
    frequency = IntegerField(default=60)
    #: when was it last checked?
    last_checked = DateTimeField(null=True)

    #: Which feed should posts from this source show up in?
    feed = ForeignKeyField(Feed, backref='external_sources')

    #: Where the actual per-type-specific settings are saved:
    settings = CharField(default='{}')

    #: Should new posts from this source start off published?
    publish = BooleanField(default=False)

    #: Which user should be set as the owner / author of these?
    post_as_user = ForeignKeyField(User, backref='external_sources')

    #: initial post settings. (TODO)
    post_template = CharField(default='{}')

    #: Lifetime start of new posts (formula)
    lifetime_start = CharField(default="NOW")
    #: Lifetime end of new posts (formula)
    lifetime_end = CharField(default="NOW + 1 WEEK")

    #: how long should each post be displayed for?
    display_time = IntegerField(default=8)

    def current_lifetime_start(self):
        ''' given the equation in the lifetime_start field, what should
            the time be of a new post start time? '''
        return datetime.fromtimestamp(eval_datetime_formula(self.lifetime_start))

    def current_lifetime_end(self):
        ''' given the equation in the lifetime_end field, what time
            should the end of a new post lifetime be? '''
        return datetime.fromtimestamp(eval_datetime_formula(self.lifetime_end))
