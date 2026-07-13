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
streetsign_server.models.users
===============================================

User, Group, and UserGroup ORM models.

The writeable_feeds / publishable_feeds methods reference Feed from .feeds
via lazy imports inside the method bodies. This is a deliberate, safe pattern
that resolves the unavoidable cyclic dependency between permissions (feeds)
and users at runtime without introducing module-level cycles.

'''

# pylint: disable=cyclic-import,import-outside-toplevel,singleton-comparison,not-an-iterable,invalid-repr-returned


import base64
import hashlib
import uuid

import bcrypt
from peewee import * # pylint: disable=wildcard-import,unused-wildcard-import

from .base import DBModel, now


def _prehash(password):
    ''' bcrypt silently truncates its input at 72 bytes. To support
        arbitrarily long passwords (and avoid that footgun) we first run the
        password through SHA-256 and base64-encode the digest, yielding a
        fixed 44-byte token that always fits within bcrypt's limit.

        Note: this is independent of SECRET_KEY - password hashes no longer
        depend on the Flask signing key, so rotating SECRET_KEY no longer
        locks every user out. '''
    digest = hashlib.sha256(password.encode('utf-8')).digest()
    return base64.b64encode(digest)


class User(DBModel):
    ''' Back-end user. '''

    validation_regexp = {
        'loginname': r'.{1,100}',
        'emailaddress': r'(^$|.*@.*\..*)'
    }

    #: the unique name user to log in
    loginname = CharField(unique=True, default=lambda: f'user_{uuid.uuid4().hex[:8]}')
    #: how the user would like to be displayed
    displayname = CharField(null=True, default="New User")
    #: how to contact the user:
    emailaddress = CharField(default='')

    #: bcrypt'd, salted, etc password hash
    passwordhash = CharField()

    #: is the user an admin?
    is_admin = BooleanField(default=False)

    #: you can lock out users, so they cannot log in for a while.
    is_locked_out = BooleanField(default=False)

    #: when was the last attempt to log in?
    last_login_attempt = DateTimeField(default=now)
    #: how many times has the user failed to log in?
    failed_logins = IntegerField(default=0)

    def set_password(self, password):
        ''' Encrypts password, and sets the password hash.
            Not stored until you save! '''

        self.passwordhash = bcrypt.hashpw(
            _prehash(password),
            bcrypt.gensalt(),
        ).decode('utf-8')

    def confirm_password(self, password):
        ''' Check that password does verify against the stored hash '''

        if not self.passwordhash:
            return False

        return bcrypt.checkpw(
            _prehash(password),
            self.passwordhash.encode('utf-8'),
        )

    def __repr__(self):
        return '<User:' + self.displayname + '>'

    def writeable_feeds(self):
        ''' Returns a list of all Feeds this user can write to. '''
        from .feeds import Feed, FeedPermission

        if self.is_admin:
            return Feed.select()

        user_feeds = {
            p.feed_id for p in
            FeedPermission.select(FeedPermission.feed)
            .where(FeedPermission.user == self,
                   FeedPermission.write == True)
        }
        group_feeds = {
            p.feed_id for p in
            FeedPermission.select(FeedPermission.feed)
            .join(UserGroup, on=FeedPermission.group == UserGroup.group)
            .where(UserGroup.user == self,
                   FeedPermission.group.is_null(False),
                   FeedPermission.write == True)
        }
        allowed = user_feeds | group_feeds
        return [f for f in Feed.select() if f.id in allowed]

    def publishable_feeds(self):
        ''' Returns all the Feeds that this user can publish to. '''
        from .feeds import Feed, FeedPermission

        if self.is_admin:
            return Feed.select()

        user_feeds = {
            p.feed_id for p in
            FeedPermission.select(FeedPermission.feed)
            .where(FeedPermission.user == self,
                   FeedPermission.publish == True)
        }
        group_feeds = {
            p.feed_id for p in
            FeedPermission.select(FeedPermission.feed)
            .join(UserGroup, on=FeedPermission.group == UserGroup.group)
            .where(UserGroup.user == self,
                   FeedPermission.group.is_null(False),
                   FeedPermission.publish == True)
        }
        allowed = user_feeds | group_feeds
        return [f for f in Feed.select() if f.id in allowed]

    def groups(self):
        ''' Returns all the Groups that this user is part of. '''

        return list(Group.select()
                         .join(UserGroup)
                         .where(UserGroup.user == self))

    def set_groups(self, groupidlist):
        ''' Set the grouplist for this user (and remove old groups) '''

        # clear old groups:
        UserGroup.delete().where(UserGroup.user == self).execute()

        group_ids = []
        for gid in groupidlist:
            try:
                group_ids.append(int(gid))
            except (ValueError, TypeError):
                continue

        if not group_ids:
            return True, self.groups()

        # fetch all groups in one query:
        groups = {g.id: g for g in
                  Group.select().where(Group.id << group_ids)}

        # set new ones:
        for gid in group_ids:
            group = groups.get(gid)
            if group is None:
                return False, 'Invalid user, or groupid'
            try:
                UserGroup(user=self, group=group).save()
            except Exception:
                return False, 'Invalid user, or groupid'

        return True, self.groups()


class Group(DBModel):
    ''' User groups (for permissions.) Groups can be given permission to
        publish/write/etc for certain Feeds, so this simplifies admin. '''

    name = CharField(unique=True)
    display = BooleanField(default=True)

    def __repr__(self):
        return '<Group:' + self.name + \
            ('(hidden)>' if not self.display else '>')

    def users(self):
        """Return all users in this group."""
        return list(User.select().join(UserGroup)
                            .where(UserGroup.group == self))

    def set_users(self, useridlist):
        """Replace the users in this group with the given list."""
        # clear old groups:
        UserGroup.delete().where(UserGroup.group == self).execute()

        user_ids = []
        for uid in useridlist:
            try:
                user_ids.append(int(uid))
            except (ValueError, TypeError):
                continue

        if not user_ids:
            return True, self.users()

        # fetch all users in one query:
        users = {u.id: u for u in
                 User.select().where(User.id << user_ids)}

        # set new ones:
        for uid in user_ids:
            user = users.get(uid)
            if user is None:
                return False, 'Invalid user'
            try:
                UserGroup(group=self, user=user).save()
            except Exception:
                return False, 'Invalid user'

        return True, self.users()


class UserGroup(DBModel):
    ''' Cross-Reference table '''
    # XREF
    user = ForeignKeyField(User, index=True)
    group = ForeignKeyField(Group, index=True)
