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
======================================
streetsign_server.models.base
======================================

Base ORM infrastructure, utility functions, and DB management.

'''

from datetime import datetime, timedelta
from time import time, mktime

from flask import json
from peewee import * # pylint: disable=wildcard-import,unused-wildcard-import

try:
    import re2 as re # pylint: disable=import-error
except ImportError:
    import re

from simpleeval import simple_eval

from streetsign_server import app

SECRET_KEY = app.config.get('SECRET_KEY')

DB = SqliteDatabase(None, pragmas={
    'journal_mode': 'wal',
    'busy_timeout': 5000,
    'foreign_keys': 1,
})


# -------------------------------------------------------------------------
# Custom Exceptions
# -------------------------------------------------------------------------

def now(timestamp=False):  # pylint: disable=no-member,not-callable
    '''Return the current datetime adjusted by TIME_OFFSET, or as a timestamp.'''
    if timestamp:
        return mktime(now(False).timetuple())
    return datetime.now() + \
           timedelta(minutes=app.config.get('TIME_OFFSET', 0))

def safe_json_load(text, default):
    ''' either parse a string from JSON into python or else return default. '''
    try:
        return json.loads(text)
    except Exception:
        return default

def eval_datetime_formula(string):
    ''' evaluate a simple date/time formula, returning a unix datetime stamp '''

    replacements = [('WEEKS', '* 604800'),
                    ('WEEK', '* 604800'),
                    ('DAYS', '* 86400'),
                    ('DAY', '* 86400'),
                    ('MONTHS', '* 2592000'),  # 30 day month...
                    ('MONTH', '* 2592000'),
                   ]

    for rep_str, out_str in replacements:
        string = string.replace(rep_str, out_str)

    return simple_eval(string, names={'NOW': time()})

def by_id(model, ids):
    ''' returns a list of objects, selected by id (list) '''
    return list(model.select().where(model.id << [int(i) for i in ids]))


# -------------------------------------------------------------------------
# Useful functions
# -------------------------------------------------------------------------

class InvalidValue(Exception):
    ''' for invalid values trying to be set by update_from '''

class PermissionDenied(Exception):
    ''' for when an unauthorized user tries to do something. '''

class InvalidPassword(Exception):
    ''' Oh no! Invalid password! '''

    def __init__(self, value):
        super().__init__(value)
        self.value = value
    def __str__(self):
        return repr(self.value)

# -------------------------------------------------------------------------
# Other
# -------------------------------------------------------------------------

class DBModel(Model):
    ''' base class for other database models '''
    # pylint: disable=too-few-public-methods

    validation_regexp = {}

    def update_from(self, form, field, formfield=None, cb=False):
        ''' convenience method for updating fields in objects from a
            submitted form. allows for a callback on failure.
            each class has a validation_regexp dict '''
        formfield = formfield if formfield else field

        try:
            value = form[formfield]
            if value == re.match(self.validation_regexp.get(field, '.*'),
                                 value).group():
                fieldtype = type(getattr(self, field))
                if fieldtype is bool and isinstance(value, str):
                    setattr(self, field, value.lower() in ('true', 'yes', 'on'))
                else:
                    setattr(self, field, value)
            else:
                raise AttributeError('Does not match regexp!')
        except KeyError:
            # not in form
            pass
        except AttributeError as exc:
            # fails regexp!
            err = f'"{value}" is not a valid {field}'
            if cb:
                cb(err)
            else:
                raise InvalidValue(err) from exc
