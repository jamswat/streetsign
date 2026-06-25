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
streetsign_server.models.screens
===============================================

Screen ORM model.

'''

from hashlib import md5

from flask import json
from peewee import * # pylint: disable=wildcard-import,unused-wildcard-import

from .base import DBModel, safe_json_load


class Screen(DBModel):
    ''' Each URL for output is known as a screen. (You can point a web-browser
        with a physical screen at it.)  This stores the info needed to display
        them.

        Since most of the settings here are made with a JS interface,
        and sent as json packets to another JS interface for display,
        and don't need to be queried against, just leave 'em as JSON.

        '''

    # TODO: have JSON list Field types here, for validation, rather than
    #       in the view/logic code...

    #: the url where this will be available ``/screens/<urlname``
    urlname = CharField(unique=True, null=False)

    #: the background image
    background = CharField(null=True)

    #: screen settings (JSON)
    settings = TextField(default='{}')
    #: general CSS settings for the whole page. Can contain selectors, etc.
    css = TextField(default='')
    #: default post settings (JSON)
    defaults = TextField(default='{}')
    #: spec all the zones (JSON)
    zones = TextField(default='[]')

    def to_dict(self):
        ''' returns a dict, ready for transmission as JSON '''

        return {
            "id":self.id,
            "urlname": self.urlname,
            "background": self.background if self.background else '',
            "settings": safe_json_load(self.settings, {}),
            "defaults": safe_json_load(self.defaults, {}),
            "css": self.css if self.css else '',
            "zones": safe_json_load(self.zones, []),
            }
    def md5(self):
        ''' return MD5 digest of this screen's JSON representation. '''
        return md5(json.dumps(self.to_dict()).encode()).hexdigest()
