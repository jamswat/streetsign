/************************************************************

    StreetSign Digital Signage Project
     (C) Copyright 2013-2026 Daniel Fairhead

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
    Display client heartbeat.

    Tells the server this screen is connected (so admins can see who is
    online), and reloads the page when the server asks for a refresh.

*************************************************************/
'use strict';

(function() {
    function screenData() {
        if (typeof SCREEN_DATA !== 'undefined' && SCREEN_DATA) {
            return SCREEN_DATA;
        }
        return window.SCREEN_DATA || null;
    }

    function startHeartbeat() {
        const data = screenData();
        if (!data || !data.id) {
            return;
        }

        const interval = (window.SCREEN_HEARTBEAT_INTERVAL || 10) * 1000;
        const alias = window.CLIENT_ALIAS || '';
        let url = '/screens/heartbeat/' + data.id;
        if (alias) {
            url += '?alias=' + encodeURIComponent(alias);
        }

        let lastRefresh = null;
        let lastServer = null;

        function beat() {
            fetch(url, {cache: 'no-store', credentials: 'same-origin'})
                .then(function(response) {
                    return response.ok ? response.json() : null;
                })
                .then(function(state) {
                    if (!state) {
                        return;
                    }
                    const serverChanged = lastServer !== null &&
                                          state.server !== lastServer;
                    const refreshChanged = lastRefresh !== null &&
                                           state.refresh !== lastRefresh;
                    if (serverChanged || refreshChanged) {
                        window.location.reload();
                        return;
                    }
                    lastServer = state.server;
                    lastRefresh = state.refresh;
                })
                .catch(function() {
                    // Offline or server unreachable; try again next tick.
                })
                .then(function() {
                    window.setTimeout(beat, interval);
                });
        }

        window.setTimeout(beat, 3000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startHeartbeat);
    } else {
        startHeartbeat();
    }
})();