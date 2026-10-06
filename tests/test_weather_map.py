'''
    Regression tests for the weather post type's coordinate-picker map.

    The picker originally used CARTO basemap tiles, but CARTO began
    requiring an API key (serving "API KEY REQUIRED" watermark tiles).
    It now uses the keyless OpenStreetMap standard tiles, so guard against
    accidentally reintroducing a keyed or watermarked tile source.
'''

# pylint: disable=missing-docstring, invalid-name

import sys
import os

sys.path.append(os.path.dirname(__file__) + '/..')

from streetsign_server.post_types import weather
from unittest_helpers import StreetSignTestCase


class WeatherMapTileTestCase(StreetSignTestCase):
    ''' The coordinate picker must use keyless OSM standard tiles. '''

    def setUp(self):
        super().setUp()
        with self.ctx():
            self.html = weather.form({})

    def test_uses_openstreetmap_tile_url(self):
        self.assertIn('https://tile.openstreetmap.org/', self.html)

    def test_uses_canonical_zxy_url(self):
        self.assertIn(
            "'https://tile.openstreetmap.org/' + zoom + '/'"
            " + wrappedX + '/' + y + '.png'",
            self.html)

    def test_no_carto_references(self):
        for token in ('cartocdn', 'basemaps', 'CARTO', 'carto.com'):
            self.assertNotIn(token, self.html)

    def test_attribution_present(self):
        self.assertIn('https://www.openstreetmap.org/copyright', self.html)
        self.assertIn('OpenStreetMap</a> contributors', self.html)


if __name__ == '__main__':
    import unittest
    unittest.main()
