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

from flask import json
from peewee import * # pylint: disable=wildcard-import,unused-wildcard-import

from .base import DBModel


class ConfigVar(DBModel):
    ''' place to store site-wide front-end-editable settings. '''
    id = CharField(primary_key=True)
    value = TextField(null=True)  # as JSON!
    description = CharField(default="Setting")

def config_var(key, default_value):
    ''' Retrieve a ConfigVar from the database, creating it with
        `default_value` if it hasn't been set yet. Returns the *value*,
        not the database record.
        '''
    result, _created = ConfigVar.get_or_create(
        id=key,
        defaults={'value': json.dumps(default_value)},
    )
    return json.loads(result.value)
