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
streetsign_server.models.config
===============================================

ConfigVar ORM model and config_var accessor function.

'''

import sqlite3

from flask import json
from peewee import * # pylint: disable=wildcard-import,unused-wildcard-import

from .base import DBModel


class ConfigVar(DBModel):
    ''' place to store site-wide front-end-editable settings. '''
    id = CharField(primary_key=True)
    value = CharField(null=True) # as JSON!
    description = CharField(default="Setting")

def config_var(key, default_value):
    ''' a 'get_or_create' type function for retrieving database ConfigVar
        values, or the default value it it hasn't been set.
        NOTE: returns the *value*, and NOT the database record!
        '''
    try:
        return json.loads(ConfigVar.get(ConfigVar.id == key).value)
    except ConfigVar.DoesNotExist:
        try:
            return default_value
        except sqlite3.IntegrityError:
            # ha! we have a race! and you lose...
            return json.loads(ConfigVar.get(ConfigVar.id == key).value)
