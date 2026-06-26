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
"""
--------------------------------------
streetsign_server.post_types.raw_html
--------------------------------------

Full HTML page with no sanitization. Scripts and arbitrary HTML are allowed.

"""

__NAME__ = 'Raw HTML'
__DESC__ = 'Full HTML page with no sanitization - scripts and styles allowed'

from flask import render_template_string

from streetsign_server.post_types import my

def form(data):
    """Form for editing a raw HTML post."""
    return render_template_string(my('form.html'), **data)

def receive(data):
    """Parse and return raw HTML post data from the form."""
    return {'type': 'raw_html',
            'content': data.get('content', '')}

def display(data):
    """Return the raw HTML content for screen display."""
    return data['content']

def screen_js():
    """Return JavaScript for screen rendering."""
    return my('screen.js')
