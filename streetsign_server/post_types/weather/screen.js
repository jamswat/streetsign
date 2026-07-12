(function () { 'use strict';

/* ================================================================
   WeatherWidget — self-contained, zone-size-aware, resilient.

   Design
   ------
   The widget builds a CSS-Grid layout whose template changes with
   the zone's aspect ratio (landscape / portrait / square) so the
   available space is used efficiently regardless of dimensions.

   A single base font-size on the container drives every internal
   dimension (all sizes are in `em`).  A binary search finds the
   largest font-size at which the content fits within the zone
   without vertical or horizontal overflow — the search only
   adjusts font-size (no DOM rebuild), so it is cheap.

   Resilience
   ----------
   • localStorage cache (24 h hard cap, 2 h stale threshold)
   • in-memory cache as localStorage fallback (private browsing)
   • exponential backoff for fetch retries (30 s → max 10 min)
   • 30-s fetch timeout via AbortController
   • offline detection (navigator.onLine + window events)
   • stale-while-revalidate: show cached data while retrying

   Cache keys include location and units so different posts or
   unit changes don't share stale data unintentionally.
   ================================================================ */

var _weatherInstances = [];

function _WeatherWidget(container, zone, cfg) {
    this.container = container;
    this.zone     = zone;
    this.cfg      = cfg || {};

    this.location = this.cfg.location || 'London';
    this.units    = this.cfg.units    || 'C';

    this._initShowMetrics();
    this._setupCacheKey();
    this._applyColors();
    this._loadCache();

    this.retryMs   = 30 * 1000;
    this.errCount  = 0;
    this.isOnline  = navigator.onLine;

    this._build();
    this._startResizeObserver();
    this._startOnlineListeners();

    if (this.cachedData) this._fill();

    this._fetch();

    this._clockTimer = setInterval(
        this._updateStatus.bind(this),
        60 * 1000
    );

    _weatherInstances.push(this);
}

_WeatherWidget.prototype = {

    _initShowMetrics: function () {
        var cfg = this.cfg;
        var DEFAULTS = {
            feels_like:     true,
            humidity:       true,
            wind_speed:     true,
            wind_direction: false,
            uv:             true,
            cloud_cover:    false,
            pressure:       false,
            visibility:     false,
            precipitation:  false,
            sun_times:      true
        };
        if (cfg.show_metrics === false) {
            this.showMetrics = {};
            for (var k in DEFAULTS) this.showMetrics[k] = false;
        } else {
            this.showMetrics = {};
            for (var k in DEFAULTS) {
                var key = 'show_' + k;
                this.showMetrics[k] = cfg[key] !== undefined ? cfg[key] : DEFAULTS[k];
            }
        }
        this.showAnyMetric = Object.values(this.showMetrics).some(function (v) { return v; });
    },

    /* ---- cache key ---- */

    _setupCacheKey: function () {
        var loc = this.location.replace(/[^a-z0-9]/gi, '_');
        this.CACHE_KEY_DATA = 'ss-weather-' + loc + '-' + this.units;
        this.CACHE_KEY_TS   = 'ss-weather-' + loc + '-' + this.units + '-ts';
    },

    /* ---- helpers ---- */

    _esc: function (s) {
        var d = document.createElement('div');
        d.textContent = String(s || '');
        return d.innerHTML;
    },

    _cap: function (s) {
        return String(s || '').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
    },

    _testStorage: function () {
        try {
            localStorage.setItem('__ssw','1');
            localStorage.removeItem('__ssw');
            return true;
        } catch (e) {
            return false;
        }
    },

    _emoji: function (code) {
        var map = {
            113:'\u2600\uFE0F',116:'\u26C5',119:'\u2601\uFE0F',122:'\u2601\uFE0F',143:'\u{1F32B}\uFE0F',
            176:'\u{1F326}\uFE0F',179:'\u{1F328}\uFE0F',182:'\u{1F327}\uFE0F',185:'\u{1F327}\uFE0F',200:'\u26C8\uFE0F',
            227:'\u{1F328}\uFE0F',230:'\u2744\uFE0F',248:'\u{1F32B}\uFE0F',260:'\u{1F32B}\uFE0F',263:'\u{1F326}\uFE0F',
            266:'\u{1F327}\uFE0F',281:'\u{1F327}\uFE0F',284:'\u{1F327}\uFE0F',293:'\u{1F326}\uFE0F',296:'\u{1F327}\uFE0F',
            299:'\u{1F327}\uFE0F',302:'\u{1F327}\uFE0F',305:'\u{1F327}\uFE0F',308:'\u{1F327}\uFE0F',311:'\u{1F327}\uFE0F',
            314:'\u{1F327}\uFE0F',317:'\u{1F327}\uFE0F',320:'\u{1F327}\uFE0F',323:'\u{1F328}\uFE0F',326:'\u{1F328}\uFE0F',
            329:'\u{1F328}\uFE0F',332:'\u2744\uFE0F',335:'\u{1F328}\uFE0F',338:'\u2744\uFE0F',350:'\u{1F327}\uFE0F',
            353:'\u{1F326}\uFE0F',356:'\u{1F327}\uFE0F',359:'\u{1F327}\uFE0F',362:'\u{1F327}\uFE0F',365:'\u{1F327}\uFE0F',
            368:'\u{1F328}\uFE0F',371:'\u2744\uFE0F',374:'\u{1F327}\uFE0F',377:'\u{1F327}\uFE0F',386:'\u26C8\uFE0F',
            389:'\u26C8\uFE0F',392:'\u26C8\uFE0F',395:'\u26C8\uFE0F'
        };
        return map[code] || '\u{1F324}\uFE0F';
    },

    _conditionClass: function (code) {
        if ([200, 386, 389, 392, 395].indexOf(code) !== -1) return 'storm';
        if ([179, 227, 230, 323, 326, 329, 332, 335, 338, 368, 371].indexOf(code) !== -1) return 'snow';
        if ([176, 182, 185, 263, 266, 281, 284, 293, 296, 299, 302, 305, 308, 311, 314, 317, 320, 350, 353, 356, 359, 362, 365, 374, 377].indexOf(code) !== -1) return 'rain';
        if ([143, 248, 260].indexOf(code) !== -1) return 'fog';
        if ([116, 119, 122].indexOf(code) !== -1) return 'cloud';
        if (code === 113) return 'clear';
        return 'cloud';
    },

    _parseClock: function (value) {
        var m = String(value || '').trim().match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i);
        if (!m) return null;
        var h = parseInt(m[1], 10);
        var min = parseInt(m[2], 10);
        var ap = m[3] ? m[3].toUpperCase() : '';
        if (ap === 'PM' && h < 12) h += 12;
        if (ap === 'AM' && h === 12) h = 0;
        if (h > 23 || min > 59) return null;
        return h * 60 + min;
    },

    _isNight: function (astro, cur) {
        if (!astro) return false;
        var sunrise = this._parseClock(astro.sunrise);
        var sunset = this._parseClock(astro.sunset);
        if (sunrise == null || sunset == null) return false;
        /* wttr.in reports sunrise/sunset in the *location's* local
           time, so compare against the location's local observation
           time (cur.localObsDateTime) rather than the browser's
           clock, which may be in a different time zone. */
        var minutes = null;
        if (cur && cur.localObsDateTime) {
            var parts = cur.localObsDateTime.split(' ');
            var t = parts.length >= 2 ? parts[1] : '';
            var parsed = this._parseClock(t);
            if (parsed != null) minutes = parsed;
        }
        if (minutes == null) {
            var now = new Date();
            minutes = now.getHours() * 60 + now.getMinutes();
        }
        return minutes < sunrise || minutes >= sunset;
    },

    _applyCondition: function (code, astro, cur) {
        var cls = this._conditionClass(code);
        this.container.classList.remove(
            'ww-cond-clear', 'ww-cond-cloud', 'ww-cond-rain',
            'ww-cond-snow', 'ww-cond-storm', 'ww-cond-fog', 'ww-night'
        );
        this.container.classList.add('ww-cond-' + cls);
        if (this._isNight(astro, cur)) this.container.classList.add('ww-night');
    },

    _normalise: function (raw) {
        var src = raw;
        if (raw && raw.data && !raw.current_condition) src = raw.data;
        var cur = src.current_condition && src.current_condition[0];
        if (!cur || !src.weather || !src.weather.length) return null;
        var area = (src.nearest_area && src.nearest_area[0]) || {
            areaName: [{value: this.location}],
            country:  [{value: ''}]
        };
        return { current_condition: [cur], weather: src.weather, nearest_area: [area] };
    },

    /* ---- localStorage + memory cache ---- */

    _loadCache: function () {
        var MAX_AGE = 24 * 60 * 60 * 1000;
        var storageOk = this._testStorage();
        var loaded = false;

        if (storageOk) {
            try {
                var d = localStorage.getItem(this.CACHE_KEY_DATA);
                var t = localStorage.getItem(this.CACHE_KEY_TS);
                if (d && t) {
                    var age = Date.now() - parseInt(t, 10);
                    if (Number.isFinite(age) && age >= 0 && age < MAX_AGE) {
                        try {
                            this.cachedData = JSON.parse(d);
                            loaded = true;
                        } catch (e) {
                            localStorage.removeItem(this.CACHE_KEY_DATA);
                            localStorage.removeItem(this.CACHE_KEY_TS);
                        }
                    } else {
                        localStorage.removeItem(this.CACHE_KEY_DATA);
                        localStorage.removeItem(this.CACHE_KEY_TS);
                    }
                }
            } catch (e) {}
        }

        if (!loaded && this._memData && this._memTs &&
            Date.now() - this._memTs < MAX_AGE) {
            this.cachedData = this._memData;
        }
    },

    _saveCache: function () {
        var ts = Date.now();
        this._memData = this.cachedData;
        this._memTs   = ts;
        if (!this._testStorage()) return;
        try {
            localStorage.setItem(this.CACHE_KEY_DATA, JSON.stringify(this.cachedData));
            localStorage.setItem(this.CACHE_KEY_TS, String(ts));
        } catch (e) {}
    },

    _purgeCache: function () {
        this.cachedData = null;
        this._memData   = null;
        this._memTs     = null;
        try {
            localStorage.removeItem(this.CACHE_KEY_DATA);
            localStorage.removeItem(this.CACHE_KEY_TS);
        } catch (e) {}
    },

    _cacheIsValid: function () {
        if (!this.cachedData) return false;
        var ts = this._cachedTs();
        if (!ts) return false;
        var age = Date.now() - ts;
        return age >= 0 && age < 24 * 60 * 60 * 1000;
    },

    _cachedTs: function () {
        try {
            var t = localStorage.getItem(this.CACHE_KEY_TS);
            if (t) {
                var n = parseInt(t, 10);
                if (Number.isFinite(n)) return n;
            }
        } catch (e) {}
        return this._memTs;
    },

    /* ---- colours ---- */

    _applyColors: function () {
        var s = this.container.style;
        s.setProperty('--ww-bg',     this.cfg.bg_color     || '#0a0a0f');
        s.setProperty('--ww-text',   this.cfg.text_color   || '#f0f0f5');
        s.setProperty('--ww-accent', this.cfg.accent_color  || '#c8b8ff');
        s.setProperty('--ww-high',   this.cfg.high_color   || '#ff8a75');
        s.setProperty('--ww-low',    this.cfg.low_color     || '#75c4f5');
        s.setProperty('--ww-rain',   this.cfg.rain_color    || '#5bbfef');
        s.setProperty('--ww-surface','rgba(255,255,255,0.06)');
        s.setProperty('--ww-border', 'rgba(255,255,255,0.10)');
    },

    /* ---- build the static DOM shell (once) ---- */

    _build: function () {
        var statusPos = this.cfg.status_position || 'header';
        var statusHtml = '<div class="ww-status"></div>';
        this.container.innerHTML =
            '<div class="weather-root">' +
                '<div class="ww-atmosphere"></div>' +
                '<div class="ww-header">' +
                    '<div class="ww-location"></div>' +
                    (statusPos === 'header' ? statusHtml : '') +
                '</div>' +
                '<div class="ww-hero"></div>' +
                '<div class="ww-metrics"></div>' +
                '<div class="ww-forecast"></div>' +
                (statusPos !== 'header' ? statusHtml : '') +
            '</div>';
        this.$root    = $(this.container).find('.weather-root');
        this.$atmos   = this.$root.find('.ww-atmosphere');
        this.$location = this.$root.find('.ww-location');
        this.$hero     = this.$root.find('.ww-hero');
        this.$metrics  = this.$root.find('.ww-metrics');
        this.$forecast = this.$root.find('.ww-forecast');
        this.$status   = this.$root.find('.ww-status');
    },

    /* ---- orientation + fit ---- */

    _orient: function () {
        var w = this.zone.clientWidth;
        var h = this.zone.clientHeight;
        if (!w || !h) return;
        var aspect = w / h;
        this.container.classList.remove(
            'ww-orient-landscape', 'ww-orient-portrait', 'ww-orient-square'
        );
        if (aspect > 1.25)      this.container.classList.add('ww-orient-landscape');
        else if (aspect < 0.8)  this.container.classList.add('ww-orient-portrait');
        else                    this.container.classList.add('ww-orient-square');
    },

    _startResizeObserver: function () {
        var self = this;
        var raf = null;
        var update = function () {
            raf = null;
            self._orient();
            self._fit();
        };
        if (typeof ResizeObserver !== 'undefined') {
            this._ro = new ResizeObserver(function () {
                if (raf) cancelAnimationFrame(raf);
                raf = requestAnimationFrame(update);
            });
            this._ro.observe(this.zone);
        }
        update();

        var self2 = this;
        setTimeout(function () { self2._fit(); }, 200);
    },

    _startOnlineListeners: function () {
        var self = this;
        this._onOnline  = function () { self.isOnline = true;  self._fetch(); self._updateStatus(); };
        this._onOffline = function () { self.isOnline = false; self._updateStatus(); };
        window.addEventListener('online',  this._onOnline);
        window.addEventListener('offline', this._onOffline);
    },

    destroy: function () {
        clearTimeout(this._fetchTimer);
        clearInterval(this._clockTimer);
        clearInterval(this._countdownTimer);
        if (this._ro && typeof this._ro.disconnect === 'function') {
            this._ro.disconnect();
        }
        if (this._onOnline)  window.removeEventListener('online',  this._onOnline);
        if (this._onOffline) window.removeEventListener('offline', this._onOffline);
        var idx = _weatherInstances.indexOf(this);
        if (idx !== -1) _weatherInstances.splice(idx, 1);
    },

    /**
     * Binary-search the largest container font-size at which the
     * root content fits inside the zone without overflow.  Only the
     * font-size CSS property is mutated — no DOM rebuild — so each
     * iteration is a cheap reflow.
     */
    _fit: function () {
        if (this.cfg.font_size_mode === 'manual' && this.cfg.font_size > 0) {
            this.container.style.fontSize = this.cfg.font_size + 'px';
            return;
        }
        var root = this.$root[0];
        if (!root) return;
        var zh = this.zone.clientHeight;
        var zw = this.zone.clientWidth;
        if (!zh || !zw) return;

        var lo = 18, hi = Math.max(600, Math.floor(zh / 3)), best = lo;

        /* Grid cells have overflow:hidden, which makes CSS Grid treat their
           min-height as 0.  When the grid container has a fixed height
           (height:100%), the grid collapses content rows to 0 and silently
           clips everything — root.scrollHeight reports no overflow even
           though content is invisible.

           To measure the true content size, temporarily relax constraints:
             - root height → auto: grid is no longer height-constrained, so
               rows size to their actual content
             - cell overflow → visible: content isn't clipped within cells,
               so it contributes to the root's scroll dimensions
             - atmosphere → hidden: its rotation pollutes scrollW/H

           With these, root.offsetHeight = total content height and
           root.scrollWidth = total content width. */
        var areas = ['.ww-header', '.ww-hero', '.ww-metrics', '.ww-forecast'];
        var savedOv = [];
        for (var a = 0; a < areas.length; a++) {
            var cel = this.$root.find(areas[a])[0];
            savedOv.push(cel ? cel.style.overflow : null);
            if (cel) cel.style.overflow = 'visible';
        }
        var savedH = root.style.height;
        root.style.height = 'auto';

        var atmos = this.$atmos[0];
        var atmosPrev = atmos ? atmos.style.display : '';
        if (atmos) atmos.style.display = 'none';

        for (var i = 0; i < 22; i++) {
            var mid = (lo + hi) / 2;
            this.container.style.fontSize = mid + 'px';

            var ovf = root.offsetHeight > zh + 2;
            if (!ovf) ovf = root.scrollWidth > root.clientWidth + 1;

            if (!ovf) { best = mid; lo = mid; }
            else { hi = mid; }
            if (hi - lo < 0.15) break;
        }

        root.style.height = savedH;
        for (var a = 0; a < areas.length; a++) {
            var cel = this.$root.find(areas[a])[0];
            if (cel) cel.style.overflow = savedOv[a];
        }
        if (atmos) atmos.style.display = atmosPrev;
        this.container.style.fontSize = best + 'px';
    },

    /* ---- data helpers ---- */

    _rainChanceForDay: function (day) {
        if (!day || !day.hourly || !day.hourly.length) return 0;
        var sum = 0;
        for (var i = 0; i < day.hourly.length; i++) {
            sum += parseInt(day.hourly[i].chanceofrain, 10) || 0;
        }
        return Math.round(sum / day.hourly.length);
    },

    _currentRain: function () {
        var h = this.cachedData &&
                this.cachedData.weather &&
                this.cachedData.weather[0] &&
                this.cachedData.weather[0].hourly;
        if (!h || !h.length) return 0;
        var idx = Math.min(Math.floor(new Date().getHours() / 3), h.length - 1);
        return parseInt(h[idx].chanceofrain, 10) || 0;
    },

    _obsTime: function (cur) {
        if (cur.localObsDateTime) {
            var parts = cur.localObsDateTime.split(' ');
            if (parts.length >= 2) return parts.slice(1).join(' ');
        }
        return cur.observation_time || '';
    },

    _formatDay: function (dateStr, n) {
        if (n === 1) return 'Tomorrow';
        var parts = String(dateStr).split('-');
        if (parts.length === 3) {
            var y = parseInt(parts[0], 10);
            var m = parseInt(parts[1], 10);
            var d = parseInt(parts[2], 10);
            if (Number.isFinite(y) && Number.isFinite(m) && Number.isFinite(d)) {
                return new Date(y, m - 1, d).toLocaleDateString('en-US', {weekday: 'short'});
            }
        }
        return new Date(dateStr).toLocaleDateString('en-US', {weekday: 'short'});
    },

    _windLabel: function (cur, showDir) {
        var dir = showDir ? this._esc(cur.winddir16Point) + ' ' : '';
        if (this.units === 'F') {
            return dir + this._esc(cur.windspeedMiles) + ' mph';
        }
        return dir + this._esc(cur.windspeedKmph) + ' km/h';
    },

    /* ---- fill content into the existing shell ---- */

    _fill: function () {
        if (!this.cachedData) return;
        var cur   = this.cachedData.current_condition[0];
        var today = this.cachedData.weather[0];
        var fc    = this.cachedData.weather.slice(1, 3);
        var astro = today.astronomy && today.astronomy[0];

        var tf   = this.units === 'F' ? 'F' : 'C';
        var desc = (cur.weatherDesc && cur.weatherDesc[0] && cur.weatherDesc[0].value) || '';

        var curEmoji = this._emoji(parseInt(cur.weatherCode, 10));
        var rainNow  = this._currentRain();
        var code = parseInt(cur.weatherCode, 10);

        this._applyCondition(code, astro, cur);
        this.$atmos.text(curEmoji);

        this.$location.text(this._cap(this.location));

        var hero =
            '<div class="ww-emoji">' + curEmoji + '</div>' +
            '<div class="ww-hero-info">' +
                '<div class="ww-temp">' +
                    this._esc(cur['temp_' + tf]) + '\u00B0' + this.units +
                '</div>' +
                '<div class="ww-condition">' + this._esc(desc) + '</div>' +
                '<div class="ww-hilo">' +
                    '<span class="ww-hi">\u2191' + this._esc(today['maxtemp' + tf]) + '\u00B0</span>' +
                    '<span class="ww-lo">\u2193' + this._esc(today['mintemp' + tf]) + '\u00B0</span>' +
                    '<span class="ww-rain ' + (rainNow === 0 ? 'zero' : '') + '">' +
                        '\u{1F4A7} ' + rainNow + '%' +
                    '</span>' +
                '</div>' +
            '</div>';
        this.$hero.html(hero);

        /* metrics */
        var sm = this.showMetrics;
        var m = '';
        if (sm.feels_like)    m += this._metric('Feels',  this._esc(cur['FeelsLike' + tf]) + '\u00B0' + this.units);
        if (sm.humidity)      m += this._metric('Humidity', this._esc(cur.humidity) + '%');
        if (sm.wind_speed || sm.wind_direction) {
            m += this._metric('Wind', this._windLabel(cur, sm.wind_direction));
        }
        if (sm.uv)            m += this._metric('UV', this._esc(cur.uvIndex));
        if (sm.cloud_cover)   m += this._metric('Cloud', this._esc(cur.cloudcover) + '%');
        if (sm.pressure) {
            m += this._metric('Pressure', this.units === 'F'
                ? this._esc(cur.pressureInches) + ' in'
                : this._esc(cur.pressure) + ' mb');
        }
        if (sm.visibility) {
            m += this._metric('Visibility', this.units === 'F'
                ? this._esc(cur.visibilityMiles) + ' mi'
                : this._esc(cur.visibility) + ' km');
        }
        if (sm.precipitation) {
            m += this._metric('Precip', this.units === 'F'
                ? this._esc(cur.precipInches) + ' in'
                : this._esc(cur.precipMM) + ' mm');
        }
        if (astro && sm.sun_times) {
            m += this._metric('Sunrise', this._esc(astro.sunrise), 'sun');
            m += this._metric('Sunset',  this._esc(astro.sunset),  'sun');
        }
        this.$metrics.html(m);

        /* forecast */
        var f = '';
        for (var i = 0; i < fc.length; i++) {
            f += this._renderDay(fc[i], i + 1, tf);
        }
        this.$forecast.html(f);

        this._updateStatus();
        this._fit();
    },

    _metric: function (label, value, cls) {
        return '<div class="ww-metric' + (cls ? ' ww-metric-' + cls : '') + '">' +
            '<span class="ww-metric-label">' + this._esc(label) + '</span>' +
            '<span class="ww-metric-value">' + value + '</span>' +
            '</div>';
    },

    _renderDay: function (day, n, tf) {
        var rain = this._rainChanceForDay(day);
        var code = parseInt(
            (day.hourly && day.hourly[4] && day.hourly[4].weatherCode) ||
            (day.hourly && day.hourly[0] && day.hourly[0].weatherCode), 10
        );
        return '<div class="ww-fc-day">' +
            '<div class="ww-fc-date">' + this._esc(this._formatDay(day.date, n)) + '</div>' +
            '<div class="ww-fc-emoji">' + this._emoji(code) + '</div>' +
            '<div class="ww-fc-temps">' +
                '<span class="ww-fc-hi">' + this._esc(day['maxtemp' + tf]) + '\u00B0</span>' +
                '<span class="ww-fc-sep">/</span>' +
                '<span class="ww-fc-lo">' + this._esc(day['mintemp' + tf]) + '\u00B0</span>' +
            '</div>' +
            '<div class="ww-fc-rain ' + (rain === 0 ? 'zero' : '') + '">' +
                '<span>\u{1F4A7} ' + rain + '%</span>' +
                '<span class="ww-fc-rain-track"><span style="width:' + rain + '%"></span></span>' +
            '</div>' +
            '</div>';
    },

    /* ---- status bar ---- */

    _updateStatus: function () {
        if (!this.$status || !this.$status.length) return;

        var ts      = this._cachedTs();
        var age     = ts ? Date.now() - ts : 0;
        var isStale = age > 2 * 60 * 60 * 1000;
        var ageText = '';
        if (ts) {
            ageText = age < 3600000
                ? Math.round(age / 60000) + 'm ago'
                : Math.round(age / 3600000) + 'h ago';
        }

        var cls = 'ww-status';
        var msg;
        if (!this.isOnline) {
            cls += ' offline';
            msg = ageText ? 'Cached ' + ageText + ' \u00B7 offline' : 'Cached \u00B7 offline';
        } else if (isStale) {
            cls += ' stale';
            msg = ageText ? 'Stale \u00B7 ' + ageText : 'Stale';
        } else if (ageText) {
            msg = 'Updated ' + ageText;
        } else {
            msg = 'Live';
        }

        this.$status.attr('class', cls);
        this.$status.html(
            '<span class="ww-stat-msg">' + this._esc(msg) + '</span>' +
            '<span class="ww-stat-dot">\u00B7</span>' +
            '<span class="ww-stat-cd"></span>'
        );
    },

    _renderError: function (reason) {
        this.$hero.html(
            '<div class="ww-error">' +
                '<div class="ww-error-title">Unable to load weather</div>' +
                '<div class="ww-error-reason">' + this._esc(reason || '') + '</div>' +
            '</div>'
        );
        this.$metrics.empty();
        this.$forecast.empty();
        this.$status.attr('class', 'ww-status offline');
        this.$status.html(
            '<span>Last attempt ' + this._esc(new Date().toLocaleTimeString()) + '</span>' +
            '<span class="ww-stat-dot">\u00B7</span>' +
            '<span>Retrying\u2026</span>'
        );
        this._fit();
    },

    /* ---- fetch + retry ---- */

    _fetch: function () {
        if (this.cfg._preview) return;
        var self = this;
        clearTimeout(this._fetchTimer);

        var MAX_AGE = 24 * 60 * 60 * 1000;
        if (this.cachedData && !this._cacheIsValid()) this._purgeCache();

        if (!this.isOnline) {
            if (this.cachedData) this._fill();
            else this._renderError('Offline');
            this._schedule(this.retryMs);
            return;
        }

        var query;
        if (this.cfg.lat != null && this.cfg.lon != null) {
            query = this.cfg.lat + ',' + this.cfg.lon;
        } else {
            query = encodeURIComponent(this.location);
        }
        var url = '/weather-proxy/' + query + '?nonce=' + Date.now();

        var ctrl = new AbortController();
        var tid  = setTimeout(function () { ctrl.abort(); }, 30 * 1000);

        fetch(url, { signal: ctrl.signal })
            .then(function (res) {
                clearTimeout(tid);
                if (!res.ok) throw new Error('HTTP ' + res.status);
                return res.json();
            })
            .then(function (json) {
                var normalised = self._normalise(json);
                if (!normalised) throw new Error('Bad data shape');
                self.cachedData = normalised;
                self._saveCache();
                self.errCount = 0;
                self.retryMs  = 30 * 1000;
                self._fill();

                var intervalMin = Math.max(5, Math.min(360,
                    self.cfg.update_interval_min || 45
                ));
                self._schedule(intervalMin * 60 * 1000);
            })
            .catch(function (e) {
                clearTimeout(tid);
                self.errCount++;
                var msg = e.name === 'AbortError'
                    ? 'Request timed out'
                    : (e.message || 'Unknown error');

                if (self.cachedData) self._fill();
                else self._renderError(msg);

                self.retryMs = Math.min(
                    self.retryMs * 1.5,
                    10 * 60 * 1000
                );
                self._schedule(self.retryMs);
            });
    },

    _schedule: function (ms) {
        var self = this;
        clearTimeout(this._fetchTimer);
        clearInterval(this._countdownTimer);

        this._fetchTimer = setTimeout(function () {
            self._fetch();
        }, ms);

        var due = Date.now() + ms;
        this._countdownTimer = setInterval(function () {
            var el = self.$status ? self.$status.find('.ww-stat-cd')[0] : null;
            if (!el) return;
            var rem = Math.max(0, due - Date.now());
            if (rem === 0) {
                el.textContent = 'Updating\u2026';
                clearInterval(self._countdownTimer);
            } else {
                var mm = Math.floor(rem / 60000);
                var ss = Math.floor((rem % 60000) / 1000);
                el.textContent = 'refresh in ' + mm + 'm ' + String(ss).padStart(2, '0') + 's';
            }
        }, 1000);
    }
};

/* ---- inject CSS exactly once ---- */

(function injectWeatherCSS() {
    if (document.getElementById('ss-weather-css')) return;
    var style = document.createElement('style');
    style.id = 'ss-weather-css';
    style.textContent = `
.post_weather {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--ww-bg, #0a0a0f);
    color: var(--ww-text, #f0f0f5);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    line-height: 1;
}
.post_weather *, .post_weather *::before, .post_weather *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

/* ---- grid shell ---- */

.weather-root {
    position: relative;
    width: 100%;
    height: 100%;
    display: grid;
    gap: 0.50em;
    padding: 0.65em 0.75em 0.55em;
    grid-template-areas: "header" "hero" "metrics" "forecast";
    grid-template-rows: auto auto auto auto;
    isolation: isolate;
    overflow: hidden;
    background:
        radial-gradient(circle at 18% 18%, rgba(255,255,255,0.20), transparent 24%),
        radial-gradient(circle at 82% 82%, rgba(255,255,255,0.12), transparent 28%),
        linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0));
}
.weather-root::before {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -3;
    background:
        linear-gradient(135deg, rgba(15,23,42,0.18), rgba(15,23,42,0.04)),
        var(--ww-bg, #0a0a0f);
}
.weather-root::after {
    content: "";
    position: absolute;
    inset: 0;
    z-index: -2;
    opacity: 0.72;
    background:
        radial-gradient(circle at 25% 30%, var(--ww-glow-a, rgba(200,184,255,0.22)), transparent 30%),
        radial-gradient(circle at 75% 55%, var(--ww-glow-b, rgba(91,191,239,0.18)), transparent 32%);
    filter: blur(0.18em);
}
.ww-atmosphere {
    position: absolute;
    right: 0;
    bottom: 0;
    z-index: -1;
    font-size: 3.2em;
    line-height: 1;
    opacity: 0.16;
    filter: blur(0.01em) saturate(1.35);
    transform: rotate(-8deg);
    pointer-events: none;
}
.ww-cond-clear { --ww-glow-a: rgba(255,214,128,0.34); --ww-glow-b: rgba(67,149,255,0.24); }
.ww-cond-cloud { --ww-glow-a: rgba(203,213,225,0.26); --ww-glow-b: rgba(125,147,179,0.22); }
.ww-cond-rain  { --ww-glow-a: rgba(91,191,239,0.32); --ww-glow-b: rgba(56,91,146,0.34); }
.ww-cond-snow  { --ww-glow-a: rgba(241,245,249,0.34); --ww-glow-b: rgba(147,197,253,0.30); }
.ww-cond-storm { --ww-glow-a: rgba(250,204,21,0.28); --ww-glow-b: rgba(139,92,246,0.36); }
.ww-cond-fog   { --ww-glow-a: rgba(226,232,240,0.28); --ww-glow-b: rgba(148,163,184,0.26); }
.ww-night      { --ww-glow-a: rgba(129,140,248,0.22); --ww-glow-b: rgba(30,64,175,0.34); }
.ww-no-atmosphere .weather-root {
    background: transparent;
}
.ww-no-atmosphere .weather-root::before {
    background: var(--ww-bg, #0a0a0f);
}
.ww-no-atmosphere .weather-root::after {
    display: none;
}
.ww-no-atmosphere .ww-atmosphere {
    visibility: hidden;
}

/* Landscape: hero on the left, metrics + forecast stacked on the right. */
.ww-orient-landscape .weather-root {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 0.82fr);
    grid-template-areas:
        "header   header"
        "hero     metrics"
        "hero     forecast";
    grid-template-rows: auto auto auto;
}
.ww-orient-landscape.ww-no-metrics .weather-root {
    grid-template-rows: auto auto;
    grid-template-areas:
        "header   header"
        "hero     forecast";
}
.ww-orient-landscape.ww-no-forecast .weather-root {
    grid-template-rows: auto auto;
    grid-template-areas:
        "header   header"
        "hero     metrics";
}
.ww-orient-landscape.ww-no-forecast.ww-no-metrics .weather-root {
    grid-template-rows: auto auto;
    grid-template-columns: 1fr;
    grid-template-areas:
        "header"
        "hero";
}

/* Square: hero spans full width, metrics + forecast side by side below. */
.ww-orient-square .weather-root {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
        "header   header"
        "hero     hero"
        "metrics  forecast";
    grid-template-rows: auto auto auto;
}
.ww-orient-square.ww-no-metrics .weather-root {
    grid-template-rows: auto auto auto;
    grid-template-areas:
        "header   header"
        "hero     hero"
        "forecast forecast";
}
.ww-orient-square.ww-no-forecast .weather-root {
    grid-template-rows: auto auto auto;
    grid-template-areas:
        "header   header"
        "hero     hero"
        "metrics  metrics";
}
.ww-orient-square.ww-no-forecast.ww-no-metrics .weather-root {
    grid-template-rows: auto auto;
    grid-template-columns: 1fr;
    grid-template-areas:
        "header"
        "hero";
}

/* Portrait: single column, vertically stacked (default template). */
.ww-orient-portrait.ww-no-forecast .weather-root {
    grid-template-rows: auto auto auto;
    grid-template-areas: "header" "hero" "metrics";
}
.ww-orient-portrait.ww-no-metrics .weather-root {
    grid-template-rows: auto auto auto;
    grid-template-areas: "header" "hero" "forecast";
}
.ww-orient-portrait.ww-no-forecast.ww-no-metrics .weather-root {
    grid-template-rows: auto auto;
    grid-template-areas: "header" "hero";
}

/* ---- header ---- */

.ww-header {
    grid-area: header;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.50em;
    min-width: 0;
}
.ww-location {
    font-weight: 800;
    font-size: 1.50em;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    flex: 1 1 auto;
}

/* ---- hero (current conditions) ---- */

.ww-hero {
    grid-area: hero;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.30em;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
}
.ww-emoji {
    font-size: 2.0em;
    line-height: 1;
    flex-shrink: 0;
    filter: drop-shadow(0 0.1em 0.22em rgba(0,0,0,0.30));
}
.ww-hero-info {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.12em;
    min-width: 0;
}
.ww-temp {
    font-weight: 800;
    font-size: 2.8em;
    line-height: 0.82;
    letter-spacing: -0.06em;
    white-space: nowrap;
    text-shadow: 0 0.05em 0.18em rgba(0,0,0,0.26);
}
.ww-condition {
    max-width: 12em;
    color: var(--ww-accent);
    font-size: 0.85em;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ww-hilo {
    display: flex;
    align-items: baseline;
    gap: 0.18em;
    font-size: 0.82em;
    font-weight: 700;
    white-space: nowrap;
}
.ww-hilo span {
    display: inline-flex;
    align-items: center;
    padding: 0.2em 0.38em;
    border-radius: 999px;
    background: rgba(0,0,0,0.16);
    border: 1px solid rgba(255,255,255,0.10);
}
.ww-hi  { color: var(--ww-high); }
.ww-lo  { color: var(--ww-low); }
.ww-rain { color: var(--ww-rain); }
.ww-rain.zero { opacity: 0.3; }

/* ---- metrics ---- */

.ww-metrics {
    grid-area: metrics;
    display: flex;
    flex-wrap: wrap;
    align-content: center;
    justify-content: center;
    gap: 0.35em;
    min-width: 0;
    overflow: hidden;
}
.ww-metric {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    flex: 1 1 calc(50% - 0.35em);
    min-width: 0;
    overflow: hidden;
    gap: 0.10em;
    padding: 0.45em 0.60em;
    border: 0.035em solid rgba(255,255,255,0.13);
    border-radius: 0.38em;
    background: rgba(255,255,255,0.085);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0.16em 0.45em rgba(0,0,0,0.12);
    backdrop-filter: blur(0.2em);
}
.ww-metric-label {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 0.55em;
    font-weight: 700;
    color: var(--ww-accent);
    opacity: 0.7;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    white-space: nowrap;
}
.ww-metric-value {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 0.90em;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
}

/* ---- forecast ---- */

.ww-forecast {
    grid-area: forecast;
    display: flex;
    gap: 0.35em;
    justify-content: center;
    align-items: center;
    align-content: center;
    min-width: 0;
    overflow: hidden;
}
.ww-fc-day {
    flex: 1 1 0;
    min-width: 0;
    max-width: none;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.12em;
    padding: 0.45em 0.60em;
    background: linear-gradient(160deg, rgba(255,255,255,0.13), rgba(255,255,255,0.055));
    border: 0.035em solid rgba(255,255,255,0.14);
    border-radius: 0.45em;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0.18em 0.55em rgba(0,0,0,0.16);
    backdrop-filter: blur(0.2em);
}
.ww-fc-date {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 0.65em;
    font-weight: 700;
    color: var(--ww-accent);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    white-space: nowrap;
}
.ww-fc-emoji { font-size: 1.50em; line-height: 1; }
.ww-fc-temps {
    font-size: 1.05em;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
}
.ww-fc-hi  { color: var(--ww-high); }
.ww-fc-lo  { color: var(--ww-low); }
.ww-fc-sep { color: var(--ww-accent); opacity: 0.45; margin: 0 0.15em; }
.ww-fc-rain {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.14em;
    font-size: 0.60em;
    font-weight: 600;
    color: var(--ww-rain);
    white-space: nowrap;
}
.ww-fc-rain-track {
    display: block;
    height: 0.48em;
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255,255,255,0.14);
}
.ww-fc-rain-track span {
    display: block;
    height: 100%;
    min-width: 0.18em;
    border-radius: inherit;
    background: var(--ww-rain);
    box-shadow: 0 0 0.4em var(--ww-rain);
}
.ww-fc-rain.zero { opacity: 0.3; }
.ww-fc-rain.zero .ww-fc-rain-track span { min-width: 0; }

/* ---- status bar ---- */

.ww-status {
    position: absolute;
    right: 0.52em;
    bottom: 0.34em;
    z-index: 2;
    font-size: 0.58em;
    color: var(--ww-text);
    opacity: 0.62;
    display: flex;
    gap: 0.36em;
    justify-content: center;
    align-items: center;
    max-width: calc(100% - 1.44em);
    padding: 0.42em 0.7em;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 999px;
    background: rgba(0,0,0,0.20);
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
    white-space: nowrap;
    overflow: hidden;
}
.ww-status.stale   { color: #ffb347; opacity: 0.85; }
.ww-status.offline { color: #ff6b6b; opacity: 0.85; }
.ww-stat-dot { opacity: 0.4; }

/* ---- corner status: reserve space below grid ---- */

.ww-status-corner .weather-root {
    padding-bottom: 2.2em;
}
.ww-status-corner .weather-root > .ww-status {
    bottom: 0;
}

/* ---- status in header bar ---- */

.ww-header .ww-status {
    position: static;
    font-size: 0.48em;
    opacity: 0.78;
    display: flex;
    gap: 0.22em;
    align-items: center;
    padding: 0.16em 0.44em;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 999px;
    background: rgba(0,0,0,0.18);
    white-space: nowrap;
    flex-shrink: 0;
    box-shadow: none;
}
.ww-header .ww-status.stale   { color: #ffb347; opacity: 0.88; }
.ww-header .ww-status.offline { color: #ff6b6b; opacity: 0.88; }

.ww-status-hidden .ww-status { display: none; }

/* ---- forced layout modes ---- */

.ww-force-landscape .weather-root {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 0.82fr) !important;
    grid-template-areas: "header header" "hero metrics" "hero forecast" !important;
    grid-template-rows: auto auto auto !important;
}
.ww-force-landscape.ww-no-metrics .weather-root {
    grid-template-rows: auto auto !important;
    grid-template-areas: "header header" "hero forecast" !important;
}
.ww-force-landscape.ww-no-forecast .weather-root {
    grid-template-rows: auto auto !important;
    grid-template-areas: "header header" "hero metrics" !important;
}
.ww-force-landscape.ww-no-forecast.ww-no-metrics .weather-root {
    grid-template-rows: auto auto !important;
    grid-template-columns: 1fr !important;
    grid-template-areas: "header" "hero" !important;
}

.ww-force-portrait .weather-root {
    grid-template-columns: 1fr !important;
    grid-template-rows: auto auto auto auto !important;
    grid-template-areas: "header" "hero" "metrics" "forecast" !important;
}
.ww-force-portrait.ww-no-metrics .weather-root {
    grid-template-rows: auto auto auto !important;
    grid-template-areas: "header" "hero" "forecast" !important;
}
.ww-force-portrait.ww-no-forecast .weather-root {
    grid-template-rows: auto auto auto !important;
    grid-template-areas: "header" "hero" "metrics" !important;
}
.ww-force-portrait.ww-no-forecast.ww-no-metrics .weather-root {
    grid-template-rows: auto auto !important;
    grid-template-areas: "header" "hero" !important;
}

.ww-force-square .weather-root {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
    grid-template-rows: auto auto auto !important;
    grid-template-areas: "header header" "hero hero" "metrics forecast" !important;
}
.ww-force-square.ww-no-metrics .weather-root {
    grid-template-rows: auto auto auto !important;
    grid-template-areas: "header header" "hero hero" "forecast forecast" !important;
}
.ww-force-square.ww-no-forecast .weather-root {
    grid-template-rows: auto auto auto !important;
    grid-template-areas: "header header" "hero hero" "metrics metrics" !important;
}
.ww-force-square.ww-no-forecast.ww-no-metrics .weather-root {
    grid-template-rows: auto auto !important;
    grid-template-columns: 1fr !important;
    grid-template-areas: "header" "hero" !important;
}

/* ---- inline metrics (pill layout) ---- */

.ww-metrics-inline .ww-metrics {
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 0.28em;
}
.ww-metrics-inline .ww-metric {
    flex: 0 0 auto;
    flex-direction: row;
    align-items: center;
    gap: 0.22em;
    padding: 0.30em 0.58em;
    border-radius: 999px;
    white-space: nowrap;
}
.ww-metrics-inline .ww-metric-label {
    font-size: 0.50em;
}
.ww-metrics-inline .ww-metric-value {
    font-size: 0.75em;
}

/* ---- error ---- */

.ww-error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.25em;
    text-align: center;
}
.ww-error-title  { font-size: 2.2em; font-weight: 700; color: #ff6b6b; }
.ww-error-reason { font-size: 1.0em; color: var(--ww-accent); opacity: 0.6; }

/* ---- user visibility toggles ---- */

.ww-no-forecast .ww-forecast { display: none; }
.ww-no-metrics  .ww-metrics  { display: none; }
.ww-no-sun .ww-metric-sun    { display: none; }
    `;
    document.head.appendChild(style);
})();

/* ---- public API ---- */

return {
    render: function (zone, data) {
        var cfg = data.content || {};

        $(zone).children('.post_weather').each(function () {
            var old = $(this).data('weather-widget');
            if (old && typeof old.destroy === 'function') old.destroy();
        }).remove();

        var $container = $('<div class="post_weather"></div>').prependTo(zone);

        var visClasses = [];
        if (cfg.show_forecast === false)   visClasses.push('ww-no-forecast');
        if (cfg.show_atmosphere === false) visClasses.push('ww-no-atmosphere');

        if (cfg.layout_mode && cfg.layout_mode !== 'auto') {
            visClasses.push('ww-force-' + cfg.layout_mode);
        }
        if (cfg.metrics_layout === 'inline') {
            visClasses.push('ww-metrics-inline');
        }
        if (cfg.status_position === 'corner') {
            visClasses.push('ww-status-corner');
        }
        if (cfg.status_position === 'hidden') {
            visClasses.push('ww-status-hidden');
        }

        var widget = new _WeatherWidget($container[0], zone, cfg);

        if (!widget.showAnyMetric)  visClasses.push('ww-no-metrics');
        if (!widget.showMetrics.sun_times) visClasses.push('ww-no-sun');

        if (visClasses.length) $container.addClass(visClasses.join(' '));

        /* Re-measure now that visibility/layout classes are applied, so the
           first fit uses the correct DOM state instead of measuring before
           classes like ww-no-metrics / ww-no-forecast are present. */
        widget._fit();

        $container.data('weather-widget', widget);

        return $container;
    }
};

})()
