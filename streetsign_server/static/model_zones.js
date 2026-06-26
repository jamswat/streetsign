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

var DEFAULT_ZONE = {
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
    var zones = config.zones.map(function(z) {
        var zone = Object.assign({ selected: false }, DEFAULT_ZONE, z);
        zone.feeds = zone.feeds.map(String);
        if (!zone.css) zone.css = '';
        return zone;
    });

    var editor = {
        background: config.background,
        settings: config.settings,
        css: config.css,
        zones: zones,
        availableFeeds: config.availableFeeds,
        availableFonts: config.availableFonts,

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

        init: function() {
            var self = this;
            this.$nextTick(function() { self.initDragResize(); });
        },

        initDragResize: function() {
            var container = document.getElementById('my_fake_screen');
            if (!container) return;
            var self = this;
            var state = null;
            var hoverEl = null;
            var EDGE = 14;
            var SNAP = 5;
            var MIN_W = 8;
            var MIN_H = 6;

            function clamp(v, lo, hi) {
                return v < lo ? lo : v > hi ? hi : v;
            }

            function cursorFor(edgeL, edgeR, edgeT, edgeB) {
                if (edgeT && edgeL) return 'nwse-resize';
                if (edgeT && edgeR) return 'nesw-resize';
                if (edgeB && edgeL) return 'nesw-resize';
                if (edgeB && edgeR) return 'nwse-resize';
                if (edgeT || edgeB) return 'ns-resize';
                if (edgeL || edgeR) return 'ew-resize';
                return 'move';
            }

            function resetCursor() {
                if (hoverEl) { hoverEl.style.cursor = ''; hoverEl = null; }
            }

            container.addEventListener('pointermove', function(e) {
                if (state) return;
                var el = e.target.closest('.fake_zone');
                if (!el) { resetCursor(); return; }
                if (el !== hoverEl) { resetCursor(); hoverEl = el; }
                var r = el.getBoundingClientRect();
                var L = e.clientX - r.left < EDGE;
                var R = r.right - e.clientX < EDGE;
                var T = e.clientY - r.top < EDGE;
                var B = r.bottom - e.clientY < EDGE;
                el.style.cursor = cursorFor(L, R, T, B);
            });

            container.addEventListener('pointerleave', function() {
                if (!state) resetCursor();
            });

            container.addEventListener('pointerdown', function(e) {
                var el = e.target.closest('.fake_zone');
                if (!el) return;
                var idx = self.getZoneIndex(el);
                if (idx < 0) return;

                var zone = self.zones[idx];
                var rect = el.getBoundingClientRect();
                var cRect = container.getBoundingClientRect();
                var cw = cRect.width;
                var ch = cRect.height;

                resetCursor();
                self.selectZone(idx);

                var nearL = e.clientX - rect.left < EDGE;
                var nearR = rect.right - e.clientX < EDGE;
                var nearT = e.clientY - rect.top < EDGE;
                var nearB = rect.bottom - e.clientY < EDGE;
                var isResize = nearL || nearR || nearT || nearB;

                el.style.cursor = cursorFor(nearL, nearR, nearT, nearB);

                state = {
                    el: el,
                    idx: idx,
                    startX: e.clientX,
                    startY: e.clientY,
                    cw: cw,
                    ch: ch,
                    sLeft: parseFloat(zone.left),
                    sTop: parseFloat(zone.top),
                    sRight: parseFloat(zone.right),
                    sBottom: parseFloat(zone.bottom),
                    edgeL: nearL, edgeR: nearR, edgeT: nearT, edgeB: nearB,
                    isResize: isResize
                };

                el.setPointerCapture(e.pointerId);
                e.preventDefault();
                e.stopPropagation();
            });

            document.addEventListener('pointermove', function(e) {
                if (!state) return;
                var zone = self.zones[state.idx];
                var dx = (e.clientX - state.startX) / state.cw * 100;
                var dy = (e.clientY - state.startY) / state.ch * 100;
                var sdx = Math.round(dx / SNAP) * SNAP;
                var sdy = Math.round(dy / SNAP) * SNAP;

                if (state.isResize) {
                    if (state.edgeL) zone.left  = clamp(state.sLeft + sdx, 0, 100 - state.sRight - MIN_W).toFixed(1) + '%';
                    if (state.edgeR) zone.right = clamp(state.sRight - sdx, 0, 100 - state.sLeft - MIN_W).toFixed(1) + '%';
                    if (state.edgeT) zone.top   = clamp(state.sTop + sdy, 0, 100 - state.sBottom - MIN_H).toFixed(1) + '%';
                    if (state.edgeB) zone.bottom = clamp(state.sBottom - sdy, 0, 100 - state.sTop - MIN_H).toFixed(1) + '%';
                } else {
                    var nl = clamp(state.sLeft + sdx, 0, state.sLeft + state.sRight);
                    var nt = clamp(state.sTop + sdy, 0, state.sTop + state.sBottom);
                    zone.left = nl.toFixed(1) + '%';
                    zone.top = nt.toFixed(1) + '%';
                    zone.right = (state.sLeft + state.sRight - nl).toFixed(1) + '%';
                    zone.bottom = (state.sTop + state.sBottom - nt).toFixed(1) + '%';
                }
            });

            document.addEventListener('pointerup', function() {
                if (state) {
                    state.el.style.cursor = '';
                    state = null;
                }
            });
        },

        getZoneIndex: function(el) {
            return parseInt(el.getAttribute('data-zone-index') || '-1');
        },

        addZone: function() {
            this.zones.push(Object.assign({ selected: false }, DEFAULT_ZONE, {
                name: 'zone' + (this.zones.length + 1)
            }));
        },

        removeZone: function(idx) {
            this.zones.splice(idx, 1);
        },

        selectZone: function(idx) {
            this.zones.forEach(function(z, i) { z.selected = (i === idx); });
        },

        selectZoneScroll: function(idx) {
            this.selectZone(idx);
            this.scrollToZoneEditor(idx);
        },

        scrollToZoneEditor: function(idx) {
            var el = document.getElementById('zone-editor-' + idx);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        },

        zoneStyle: function(zone) {
            return {
                top: zone.top || '30%',
                left: zone.left || '30%',
                right: zone.right || '30%',
                bottom: zone.bottom || '30%',
                color: zone.color || '#fff',
                fontFamily: zone.fontfamily || ''
            };
        },

        initChoices: function(el) {
            new Choices(el, { searchEnabled: true, itemSelectText: '', shouldSort: false });
        }
    };

    return editor;
};
