# -*- coding: utf-8 -*-
#  StreetSign Digital Signage Project
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
"""
-----------------------------------
streetsign_server.post_types.weather
-----------------------------------

Live weather display from wttr.in.  Fetches current conditions and a
2-day forecast and renders them in a zone-size-aware widget.

Configuration
-------------
location : str (required)
    Place name passed to wttr.in (e.g. "London", "Rabaul").
lat : float (optional)
    Latitude for pinpoint lookups — overrides geocoding when set.
lon : float (optional)
    Longitude for pinpoint lookups.
units : str  (default "C")
    "C" for Celsius (default) or "F" for Fahrenheit.

Appearance
----------
bg_color : str (default "#0a0a0f")
    Widget background colour (hex).
text_color : str (default "#f0f0f5")
    Primary text colour.
accent_color : str (default "#c8b8ff")
    Accent colour used for the separator line and muted text.
high_color : str (default "#ff8a75")
    High-temperature colour.
low_color : str (default "#75c4f5")
    Low-temperature colour.
rain_color : str (default "#5bbfef")
    Rain percentage colour.

show_forecast : bool (default True)
    Show the 2-day forecast cards below the current conditions.
show_metrics : bool (default True)
    Show the feels-like / humidity / wind / UV / sunrise / sunset row.
show_sun_times : bool (default True)
    Include sunrise and sunset in the metrics row (requires show_metrics).
show_atmosphere : bool (default True)
    Use weather-aware gradients and the large ambient condition icon.

update_interval_min : int (default 45)
    How often (in minutes) to fetch fresh data from wttr.in.
"""

__NAME__ = 'Weather'
__DESC__ = 'Live weather forecast from wttr.in'

from flask import render_template_string

from streetsign_server.post_types import my


def form(data):
    return render_template_string(my('form.html'), **data)


def receive(data):
    lat = None
    lon = None
    raw_lat = (data.get('lat', '') or '').strip()
    raw_lon = (data.get('lon', '') or '').strip()
    if raw_lat and raw_lon:
        try:
            lat = float(raw_lat)
            lon = float(raw_lon)
            if lat < -90 or lat > 90 or lon < -180 or lon > 180:
                lat = None
                lon = None
            elif (lat != lat) or (lon != lon):  # NaN guard
                lat = None
                lon = None
        except (ValueError, TypeError):
            pass

    def safe_int(val, default=45, lo=5, hi=360):
        try:
            v = int(str(val or '').strip() or default)
        except (ValueError, TypeError):
            v = default
        return max(lo, min(hi, v))

    return {
        'location': (data.get('location', '') or 'London').strip() or 'London',
        'lat': lat,
        'lon': lon,
        'units': data.get('units', 'C') if data.get('units') in ('C', 'F') else 'C',
        'bg_color': data.get('bg_color', '#0a0a0f') or '#0a0a0f',
        'text_color': data.get('text_color', '#f0f0f5') or '#f0f0f5',
        'accent_color': data.get('accent_color', '#c8b8ff') or '#c8b8ff',
        'high_color': data.get('high_color', '#ff8a75') or '#ff8a75',
        'low_color': data.get('low_color', '#75c4f5') or '#75c4f5',
        'rain_color': data.get('rain_color', '#5bbfef') or '#5bbfef',
        'show_forecast': 'show_forecast' in data,
        'show_metrics': 'show_metrics' in data,
        'show_sun_times': 'show_sun_times' in data,
        'show_atmosphere': 'show_atmosphere' in data,
        'update_interval_min': safe_int(data.get('update_interval_min')),
    }


def display(data):
    return data


def screen_js():
    return my('screen.js')
