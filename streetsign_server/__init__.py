# -*- coding: utf-8 -*-
"""  StreetSign Digital Signage Project
     (C) Copyright 2013 Daniel Fairhead

    StreetSign is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    StreetSign is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with StreetSign.  If not, see <http://www.gnu.org/licenses/>.

"""

from flask import Flask

try:
    import config
except ImportError:
    print("Config file missing, using defaults.")
    import config_default as config

app = Flask(__name__) # pylint: disable=invalid-name
app.config.from_object(config)

from . import models
import streetsign_server.views as views
from .models import DB, ALL_MODELS, \
     User, Group, Post, Feed, FeedPermission

DB.init(app.config.get('DATABASE_FILE'))
DB.bind(ALL_MODELS)

