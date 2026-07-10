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
=======================================
streetsign_server.models
=======================================

peewee ORM database models.

'''

import logging

from .base import (DB, by_id, now, safe_json_load,
                    eval_datetime_formula, DBModel,
                    InvalidValue, PermissionDenied, InvalidPassword,
                    SECRET_KEY, app)
from .users import User, Group, UserGroup
from .auth import UserSession, user_login, user_logout, get_logged_in_user
from .feeds import Feed, FeedPermission, Post, ExternalSource
from .screens import Screen
from .config import ConfigVar, config_var

logger = logging.getLogger(__name__)

ALL_MODELS = (User, UserSession, Group, UserGroup, Post, Feed,
              FeedPermission, ConfigVar, ExternalSource, Screen)

def init(dbfile=False):
    """Initialise the database connection."""
    if dbfile:
        DB.init(dbfile)
    else:
        DB.init(app.config.get('DATABASE_FILE'))
    DB.bind(ALL_MODELS)

def create_all(dbfile=False):
    """Create all database tables."""
    init(dbfile)
    for t in ALL_MODELS:
        t.create_table(True)

def migrations(dbfile=False):
    """Run database migrations."""
    # pylint: disable=import-outside-toplevel
    from peewee import TextField, IntegerField
    from playhouse.migrate import SqliteMigrator, migrate

    init(dbfile)

    migrator = SqliteMigrator(DB)

    post_fields = DB.get_columns('Post')
    post_field_names = [x[0] for x in post_fields]  # 0: name of column

    # Migration 1: add post title
    if 'title' not in post_field_names:
        logger.info('running migration 1 - add post title')
        post_title = TextField(default='')
        migrate(
            migrator.add_column('Post', 'title', post_title)
        )

    # Migration 2: add post font size
    if 'fontsize' not in post_field_names:
        logger.info('running migration 2 - add post font size')
        post_fontsize = IntegerField(null=True)
        migrate(
            migrator.add_column('Post', 'fontsize', post_fontsize)
        )

    # Migration 3: merge 'complex' post type into 'html'
    complex_count = Post.select().where(Post.type == 'complex').count()
    if complex_count > 0:
        logger.info('running migration 3 - merge complex post type into html'
                     ' (%s posts)', complex_count)
        Post.update(type='html').where(Post.type == 'complex').execute()

    # Migration 4: add post sort_order for playlist ordering
    if 'sort_order' not in post_field_names:
        logger.info('running migration 4 - add post sort_order')
        post_sort_order = IntegerField(default=0)
        migrate(
            migrator.add_column('Post', 'sort_order', post_sort_order)
        )

    # Migration 5: add post recurrence for day-of-week scheduling
    if 'recurrence' not in post_field_names:
        logger.info('running migration 5 - add post recurrence')
        post_recurrence = TextField(
            default='{"enabled":false,"days":[]}')
        migrate(
            migrator.add_column('Post', 'recurrence', post_recurrence)
        )


__all__ = ['DB', 'user_login', 'user_logout', 'get_logged_in_user',
           'User', 'Group', 'Post', 'Feed', 'FeedPermission', 'UserGroup',
           'ConfigVar', 'Screen', 'config_var', 'UserSession', 'ExternalSource',
           'init', 'create_all', 'by_id', 'migrations']
