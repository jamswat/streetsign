/*global Alpine */
/************************************************************

    StreetSign Digital Signage Project
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

    ---------------------------------
    Screen Zones Editor - Alpine.js data factory

*************************************************************/
'use strict';

const DEFAULT_ZONE = {
    name: 'zone',
    top: '30%',
    left: '30%',
    right: '30%',
    bottom: '30%',
    type: 'fade',
    color: '#fff',
    fontfamily: '',
    fadetime: 250,
    feeds: [],
    css: ''
};

window.makeScreenEditor = function(config) {
    const zones = config.zones.map(function(z) {
        const zone = Object.assign({ selected: false }, DEFAULT_ZONE, z);
        zone.feeds = zone.feeds.map(String);
        if (!zone.css) zone.css = '';
        return zone;
    });

    return {
        background: config.background,
        settings: config.settings,
        css: config.css,
        zones: zones,
        availableFeeds: config.availableFeeds,
        availableFonts: config.availableFonts,
        zoneTypes: config.zoneTypes,

        get serializedZones() {
            return JSON.stringify(this.zones.map(function(z) {
                return {
                    name: z.name,
                    top: z.top,
                    left: z.left,
                    right: z.right,
                    bottom: z.bottom,
                    type: z.type,
                    color: z.color,
                    fontfamily: z.fontfamily,
                    fadetime: z.fadetime,
                    feeds: z.feeds.map(Number),
                    css: z.css
                };
            }));
        },

        addZone() {
            this.zones.push(Object.assign({ selected: false }, DEFAULT_ZONE, {
                name: 'zone' + (this.zones.length + 1)
            }));
        },

        removeZone(idx) {
            this.zones.splice(idx, 1);
        },

        selectZone(idx) {
            this.zones.forEach(function(z, i) { z.selected = (i === idx); });
        },

        selectZoneScroll(idx) {
            this.selectZone(idx);
            this.scrollToZoneEditor(idx);
        },

        scrollToZoneEditor(idx) {
            const el = document.getElementById('zone-editor-' + idx);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        },

        zoneStyle(zone) {
            return {
                top: zone.top || '30%',
                left: zone.left || '30%',
                right: zone.right || '30%',
                bottom: zone.bottom || '30%',
                color: zone.color || '#fff',
                fontFamily: zone.fontfamily || ''
            };
        },

        initChoices(el) {
            new Choices(el, { searchEnabled: true, itemSelectText: '', shouldSort: false });
        }
    };
};
