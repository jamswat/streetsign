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
'''
Backward-compatibility shim.  The 'complex' type has been merged into
the 'html' (Rich Text) post type.  This stub keeps existing complex posts
working by re-exporting from html, while storing 'complex' as the type
for backward database compatibility.
'''

from streetsign_server.post_types.html import *

__NAME__ = 'Advanced Document / HTML'
__DESC__ = 'Complex HTML (deprecated - use Rich Text instead)'

# Override receive to keep the 'complex' type label for existing posts.
# All other functions (form, display, screen_js, delete) come from html.

_html_receive = receive

def receive(data):
    result = _html_receive(data)
    result['type'] = 'complex'
    return result
