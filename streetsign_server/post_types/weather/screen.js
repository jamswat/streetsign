{
    render(zone, data) {
        var cfg = data.content || {};
        var $container = $(
            '<div class="post_weather"></div>'
        ).prependTo(zone);

        new _WeatherWidget($container[0], zone, cfg);

        return $container;
    }
}

/* ================================================================
   WeatherWidget — self-contained, zone-size-aware, resilient.
   ================================================================

   Lifecycle
   ---------
   The widget renders immediately into a container element.  It
   checks localStorage for a previous cache; if one exists and is
   within the 24 h cap it paints instantly.  In the background it
   fetches wttr.in and updates the display.

   Zone-size adaptation
   --------------------
   A ResizeObserver watches the zone element.  Based on available
   height and width the widget picks one of three layouts:

      compact   height < 180 px  or  width < 250 px
      medium    180 ≤ height < 350 px
      full      height ≥ 350 px

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

    this._setupCacheKey();
    this._applyColors();
    this._loadCache();

    this.retryMs   = 30 * 1000;
    this.errCount  = 0;
    this.isOnline  = navigator.onLine;

    this._renderShell();
    this._startResizeObserver();

    if (this.cachedData) this._paint();
    this._fetch();

    // Keep-alive: if we already had data, redraw periodically
    // so live-time placeholders stay current even without a fetch.
    this._clockTimer = setInterval(
        this._paint.bind(this),
        60 * 1000
    );

    _weatherInstances.push(this);
}

_WeatherWidget.prototype = {

    // ---- cache key ----

    _setupCacheKey: function () {
        var loc = this.location.replace(/[^a-z0-9]/gi, '_');
        this.CACHE_KEY_DATA = 'ss-weather-' + loc + '-' + this.units;
        this.CACHE_KEY_TS   = 'ss-weather-' + loc + '-' + this.units + '-ts';
    },

    // ---- helpers ----

    _esc: function (s) {
        var d = document.createElement('div');
        d.textContent = String(s || '');
        return d.innerHTML;
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
            113:'☀️',116:'⛅',119:'☁️',122:'☁️',143:'🌫️',
            176:'🌦️',179:'🌨️',182:'🌧️',185:'🌧️',200:'⛈️',
            227:'🌨️',230:'❄️',248:'🌫️',260:'🌫️',263:'🌦️',
            266:'🌧️',281:'🌧️',284:'🌧️',293:'🌦️',296:'🌧️',
            299:'🌧️',302:'🌧️',305:'🌧️',308:'🌧️',311:'🌧️',
            314:'🌧️',317:'🌧️',320:'🌧️',323:'🌨️',326:'🌨️',
            329:'🌨️',332:'❄️',335:'🌨️',338:'❄️',350:'🌧️',
            353:'🌦️',356:'🌧️',359:'🌧️',362:'🌧️',365:'🌧️',
            368:'🌨️',371:'❄️',374:'🌧️',377:'🌧️',386:'⛈️',
            389:'⛈️',392:'⛈️',395:'⛈️'
        };
        return map[code] || '🌤️';
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

    // ---- localStorage + memory cache ----

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

    // ---- colours ----

    _applyColors: function () {
        var s = this.container.style;
        s.setProperty('--ww-bg',     this.cfg.bg_color     || '#0a0a0f');
        s.setProperty('--ww-text',   this.cfg.text_color   || '#f0f0f5');
        s.setProperty('--ww-accent', this.cfg.accent_color  || '#c8b8ff');
        s.setProperty('--ww-high',   this.cfg.high_color   || '#ff8a75');
        s.setProperty('--ww-low',    this.cfg.low_color     || '#75c4f5');
        s.setProperty('--ww-rain',   this.cfg.rain_color    || '#5bbfef');
        s.setProperty('--ww-surface','rgba(255,255,255,0.05)');
        s.setProperty('--ww-border', 'rgba(255,255,255,0.08)');
    },

    // ---- render shell (empty structure, filled by _paint) ----

    _renderShell: function () {
        this.container.innerHTML =
            '<div class="weather-root">' +
                '<div class="weather-inner">...</div>' +
                '<div class="weather-status"></div>' +
            '</div>';
        this.$root  = $(this.container).find('.weather-root');
        this.$inner = this.$root.find('.weather-inner');
        this.$status = this.$root.find('.weather-status');
    },

    // ---- ResizeObserver → layout mode ----

    _startResizeObserver: function () {
        var self = this;
        if (typeof ResizeObserver === 'undefined') {
            self._layoutMode = self._chooseLayout(
                self.zone.offsetHeight, self.zone.offsetWidth
            );
            return;
        }
        this._ro = new ResizeObserver(function () {
            var h = self.zone.offsetHeight;
            var w = self.zone.offsetWidth;
            var mode = self._chooseLayout(h, w);
            if (mode !== self._layoutMode) {
                self._layoutMode = mode;
                if (self.cachedData) self._paint();
            }
        });
        this._ro.observe(this.zone);
        this._layoutMode = this._chooseLayout(
            this.zone.offsetHeight, this.zone.offsetWidth
        );
    },

    _chooseLayout: function (h, w) {
        if (h < 180 || w < 250) return 'compact';
        if (h < 350) return 'medium';
        return 'full';
    },

    // ---- data helpers ----

    _rainChanceForDay: function (day) {
        if (!day || !day.hourly || !day.hourly.length) return 0;
        var vals = [];
        for (var i = 0; i < day.hourly.length; i++) {
            var r = parseInt(day.hourly[i].chanceofrain, 10) || 0;
            vals.push(r);
        }
        var sum = 0;
        for (var j = 0; j < vals.length; j++) sum += vals[j];
        return Math.round(sum / vals.length);
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

    // ---- main paint ----

    _paint: function () {
        if (!this.cachedData) return;
        var cur   = this.cachedData.current_condition[0];
        var today = this.cachedData.weather[0];
        var fc    = this.cachedData.weather.slice(1, 3);
        var area  = this.cachedData.nearest_area[0];
        var astro = today.astronomy && today.astronomy[0];

        var locName = this.location;
        var curEmoji = this._emoji(parseInt(cur.weatherCode, 10));
        var rainNow  = this._currentRain();
        var ts       = this._cachedTs();
        var age      = ts ? Date.now() - ts : 0;
        var isStale  = age > 2 * 60 * 60 * 1000;
        var ageText  = '';
        if (ts) {
            ageText = age < 3600000
                ? Math.round(age / 60000) + 'm ago'
                : Math.round(age / 3600000) + 'h ago';
        }
        var statusClass = '';
        var statusMsg   = 'Updated ' + new Date().toLocaleTimeString();
        if (isStale)  statusClass += 'stale';
        if (!this.isOnline) {
            statusClass += ' offline';
            statusMsg = ageText ? 'Cached ' + ageText + ' · offline' : 'Cached · offline';
        } else if (ageText) {
            statusMsg = 'Updated ' + ageText;
        }
        var obsTxt = this._obsTime(cur);
        if (obsTxt) statusMsg += ' · Obs ' + obsTxt;
        if (statusClass) statusClass = ' ' + statusClass.trim();

        var showFc  = this.cfg.show_forecast;
        var showMet = this.cfg.show_metrics;
        var showSun = this.cfg.show_sun_times && showMet;
        var mode    = this._layoutMode || 'full';

        var html = '';

        html += '<div class="ww-location">' + this._esc(locName) + '</div>';

        // ---- current row (all modes) ----
        html += '<div class="ww-current-row">';
        html += '<span class="ww-emoji">' + curEmoji + '</span>';
        html += '<span class="ww-temp">' + this._esc(cur.temp_C) + '°' + this.units + '</span>';
        if (mode !== 'compact') {
            html += '<span class="ww-desc">' + this._esc(cur.weatherDesc[0].value) + '</span>';
        }
        html += '</div>';

        // ---- hi / lo / rain (all modes) ----
        html += '<div class="ww-hilo-row">';
        html += '<span class="ww-hi">↑' + this._esc(today.maxtempC) + '°</span>';
        html += '<span class="ww-hi-lo-sep">/</span>';
        html += '<span class="ww-lo">↓' + this._esc(today.mintempC) + '°</span>';
        html += '<span class="ww-rain-pill ' + (rainNow === 0 ? 'no-rain' : '') + '">💧 ' + rainNow + '%</span>';
        html += '</div>';

        // ---- metrics (medium + full) ----
        if (mode !== 'compact' && showMet) {
            html += '<div class="ww-metrics">';
            html += this._metric('Feels Like', this._esc(cur.FeelsLikeC) + '°' + this.units);
            html += this._metric('Humidity',  this._esc(cur.humidity) + '%');
            html += this._metric('Wind',      this._esc(cur.windspeedKmph) + ' km/h');
            html += this._metric('UV',        this._esc(cur.uvIndex));
            if (showSun && astro) {
                html += this._metric('Sunrise', this._esc(astro.sunrise));
                html += this._metric('Sunset',  this._esc(astro.sunset));
            }
            html += '</div>';
        }

        // ---- forecast (full only) ----
        if (mode === 'full' && showFc) {
            html += '<div class="ww-forecast"><div class="ww-fc-label">Forecast</div>';
            html += '<div class="ww-fc-days">';
            for (var i = 0; i < fc.length; i++) {
                html += this._renderDay(fc[i], i + 1);
            }
            html += '</div></div>';
        }

        this.$inner.html(html);

        // ---- status bar ----
        this.$status.html(
            '<span class="ww-stat-msg">' + this._esc(statusMsg) + '</span>' +
            '<span class="ww-stat-dot">·</span>' +
            '<span class="ww-stat-cd" id="ww-stat-cd"></span>'
        );
        if (statusClass) this.$status.attr('class', 'weather-status' + statusClass);
    },

    _metric: function (label, value) {
        return '<div class="ww-metric">' +
            '<span class="ww-metric-label">' + this._esc(label) + '</span>' +
            '<span class="ww-metric-value">' + value + '</span>' +
            '</div>';
    },

    _renderDay: function (day, n) {
        var rain = this._rainChanceForDay(day);
        var code = parseInt(
            (day.hourly && day.hourly[4] && day.hourly[4].weatherCode) ||
            (day.hourly && day.hourly[0] && day.hourly[0].weatherCode), 10
        );
        return '<div class="ww-fc-day">' +
            '<div class="ww-fc-date">' + this._esc(this._formatDay(day.date, n)) + '</div>' +
            '<div class="ww-fc-emoji">' + this._emoji(code) + '</div>' +
            '<div class="ww-fc-temp">' +
                '<span class="ww-fc-hi">' + this._esc(day.maxtempC) + '°</span>' +
                '<span class="ww-fc-sep">/</span>' +
                '<span class="ww-fc-lo">' + this._esc(day.mintempC) + '°</span>' +
            '</div>' +
            '<div class="ww-fc-rain ' + (rain === 0 ? 'no-rain' : '') + '">💧 ' + rain + '%</div>' +
            '</div>';
    },

    _renderError: function (reason) {
        this.$inner.html(
            '<div class="ww-error">' +
                '<div class="ww-error-title">Unable to load weather</div>' +
                '<div class="ww-error-reason">' + this._esc(reason || '') + '</div>' +
            '</div>'
        );
        this.$status.html(
            '<span>Last attempt: ' + this._esc(new Date().toLocaleTimeString()) + '</span>' +
            '<span class="ww-stat-dot">·</span>' +
            '<span>Retrying…</span>'
        );
        this.$status.attr('class', 'weather-status offline');
    },

    // ---- fetch + retry ----

    _fetch: function () {
        var self = this;
        clearTimeout(this._fetchTimer);

        var MAX_AGE = 24 * 60 * 60 * 1000;
        if (this.cachedData && !this._cacheIsValid()) this._purgeCache();

        if (!navigator.onLine) {
            if (this.cachedData) this._paint();
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
        var url = 'https://wttr.in/' + query + '?format=j1&u=' + this.units +
                  '&nonce=' + Date.now();

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
                self._paint();

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

                if (self.cachedData) self._paint();
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
            var el = document.getElementById('ww-stat-cd');
            if (!el) return;
            var rem = Math.max(0, due - Date.now());
            if (rem === 0) {
                el.textContent = 'Updating…';
                clearInterval(self._countdownTimer);
            } else {
                var m = Math.floor(rem / 60000);
                var s = Math.floor((rem % 60000) / 1000);
                el.textContent = m + 'm ' + String(s).padStart(2, '0') + 's';
            }
        }, 1000);
    }
};

// ---- inject CSS exactly once ----

(function injectWeatherCSS() {
    if (document.getElementById('ss-weather-css')) return;
    var style = document.createElement('style');
    style.id = 'ss-weather-css';
    style.textContent =
        '.post_weather { ' +
            'width:100%; height:100%; display:flex; flex-direction:column; ' +
            'background:var(--ww-bg, #0a0a0f); overflow:hidden; ' +
        '} ' +
        '.weather-root { ' +
            'flex:1; display:flex; flex-direction:column; ' +
            'justify-content:center; align-items:center; text-align:center; ' +
            'padding:2% 3%; ' +
        '} ' +
        '.weather-inner { width:100%; } ' +

        /* Location */
        '.ww-location { ' +
            'color:var(--ww-text); font-weight:800; ' +
            'text-transform:uppercase; letter-spacing:0.04em; ' +
            'font-size:clamp(18px, 10cqh, 80px); line-height:1.1; ' +
        '} ' +

        /* Current row */
        '.ww-current-row { ' +
            'display:flex; align-items:center; justify-content:center; ' +
            'gap:clamp(4px, 2%, 20px); margin:clamp(2px, 0.8cqh, 10px) 0; ' +
        '} ' +
        '.ww-emoji { font-size:clamp(22px, 13cqh, 100px); line-height:1; flex-shrink:0; } ' +
        '.ww-temp { ' +
            'color:var(--ww-text); font-weight:800; ' +
            'font-size:clamp(28px, 18cqh, 140px); line-height:0.9; ' +
            'letter-spacing:-0.02em; ' +
        '} ' +
        '.ww-desc { ' +
            'color:var(--ww-accent); font-weight:500; ' +
            'font-size:clamp(11px, 4cqh, 32px); text-transform:capitalize; ' +
        '} ' +

        /* Hi / Lo / Rain */
        '.ww-hilo-row { ' +
            'display:flex; align-items:center; justify-content:center; ' +
            'gap:clamp(8px, 2%, 24px); ' +
        '} ' +
        '.ww-hi { color:var(--ww-high); font-weight:700; ' +
            'font-size:clamp(14px, 5cqh, 44px); } ' +
        '.ww-hi-lo-sep { color:var(--ww-accent); opacity:0.5; ' +
            'font-size:clamp(14px, 5cqh, 44px); } ' +
        '.ww-lo { color:var(--ww-low); font-weight:700; ' +
            'font-size:clamp(14px, 5cqh, 44px); } ' +
        '.ww-rain-pill { font-weight:700; font-size:clamp(14px, 5cqh, 44px); ' +
            'color:var(--ww-rain); transition:opacity 0.3s; } ' +
        '.ww-rain-pill.no-rain { opacity:0.25; color:var(--ww-accent); } ' +

        /* Metrics */
        '.ww-metrics { ' +
            'display:flex; gap:clamp(8px, 3%, 40px); flex-wrap:wrap; ' +
            'justify-content:center; margin:clamp(4px, 1.5cqh, 16px) 0; ' +
        '} ' +
        '.ww-metric { display:flex; flex-direction:column; align-items:center; gap:1px; } ' +
        '.ww-metric-label { ' +
            'font-size:clamp(8px, 2cqh, 18px); font-weight:700; ' +
            'text-transform:uppercase; letter-spacing:0.1em; ' +
            'color:var(--ww-accent); opacity:0.65; ' +
        '} ' +
        '.ww-metric-value { ' +
            'font-size:clamp(14px, 5cqh, 44px); font-weight:700; ' +
            'color:var(--ww-text); letter-spacing:-0.02em; ' +
        '} ' +

        /* Forecast */
        '.ww-forecast { width:100%; margin-top:clamp(6px, 1.5cqh, 18px); } ' +
        '.ww-fc-label { ' +
            'font-size:clamp(9px, 2cqh, 18px); font-weight:700; ' +
            'text-transform:uppercase; letter-spacing:0.1em; ' +
            'color:var(--ww-accent); opacity:0.65; margin-bottom:clamp(3px, 0.6cqh, 8px); ' +
        '} ' +
        '.ww-fc-days { ' +
            'display:flex; gap:clamp(6px, 2%, 20px); justify-content:center; ' +
            'flex-wrap:wrap; ' +
        '} ' +
        '.ww-fc-day { ' +
            'flex:1; min-width:80px; max-width:200px; ' +
            'background:var(--ww-surface); border:1px solid var(--ww-border); ' +
            'border-radius:clamp(6px, 1.5%, 14px); ' +
            'padding:clamp(6px, 1.2%, 16px) clamp(8px, 2%, 20px); ' +
            'display:flex; flex-direction:column; align-items:center; gap:2px; ' +
        '} ' +
        '.ww-fc-date { ' +
            'font-size:clamp(9px, 2.2cqh, 20px); font-weight:700; ' +
            'text-transform:uppercase; letter-spacing:0.08em; ' +
            'color:var(--ww-accent); opacity:0.7; ' +
        '} ' +
        '.ww-fc-emoji { font-size:clamp(16px, 6cqh, 56px); line-height:1.2; } ' +
        '.ww-fc-temp { ' +
            'font-size:clamp(12px, 3.5cqh, 32px); font-weight:700; ' +
            'letter-spacing:-0.02em; ' +
        '} ' +
        '.ww-fc-hi { color:var(--ww-high); } ' +
        '.ww-fc-sep { color:var(--ww-accent); opacity:0.5; margin:0 0.15em; } ' +
        '.ww-fc-lo { color:var(--ww-low); } ' +
        '.ww-fc-rain { font-size:clamp(10px, 2.5cqh, 24px); font-weight:600; ' +
            'color:var(--ww-rain); } ' +
        '.ww-fc-rain.no-rain { opacity:0.25; color:var(--ww-accent); } ' +

        /* Status bar */
        '.weather-status { ' +
            'font-size:clamp(7px, 1.6cqh, 16px); ' +
            'color:var(--ww-accent); opacity:0.5; ' +
            'display:flex; gap:0.5em; justify-content:center; padding:1% 0; ' +
        '} ' +
        '.weather-status.stale { color:#ffb347; opacity:0.8; } ' +
        '.weather-status.offline { color:#ff6b6b; opacity:0.8; } ' +
        '.ww-stat-dot { opacity:0.4; } ' +

        /* Error */
        '.ww-error { text-align:center; } ' +
        '.ww-error-title { ' +
            'font-size:clamp(14px, 5cqh, 48px); font-weight:700; ' +
            'color:#ff6b6b; ' +
        '} ' +
        '.ww-error-reason { ' +
            'font-size:clamp(10px, 3cqh, 28px); ' +
            'color:var(--ww-accent); opacity:0.6; margin-top:4px; ' +
        '} ' +

        /* Container queries for zone-awareness */
        '.post_weather { container-type:size; } ' +

        /* Very small — hide secondary in compact */
        '@container (max-height: 120px) { ' +
            '.ww-desc { display:none; } ' +
        '} ';

    document.head.appendChild(style);
})();
