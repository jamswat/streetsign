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
    Admin "Connected Clients" page.

*************************************************************/
'use strict';

(function() {
    function targetFor(client) {
        if (client.alias) {
            return 'alias:' + client.alias;
        }
        if (client.screen) {
            return 'screen:' + client.screen;
        }
        return '';
    }

    function relTime(iso) {
        const then = Date.parse(iso);
        if (isNaN(then)) {
            return iso;
        }
        const secs = Math.max(0, Math.round((Date.now() - then) / 1000));
        if (secs < 5) {
            return 'just now';
        }
        if (secs < 60) {
            return secs + 's ago';
        }
        return Math.floor(secs / 60) + 'm ago';
    }

    function esc(text) {
        const div = document.createElement('div');
        div.textContent = text === null || text === undefined ? '' : String(text);
        return div.innerHTML;
    }

    function render(clients) {
        const body = document.getElementById('clients-body');
        if (!body) {
            return;
        }

        body.innerHTML = '';

        clients.forEach(function(client) {
            const target = targetFor(client);
            const tr = document.createElement('tr');
            tr.dataset.target = target;
            const action = target
                ? '<button type="button" class="btn btn-outline-secondary btn-sm refresh-client">Refresh</button>'
                : '';

            tr.innerHTML =
                '<td><span class="badge bg-success">online</span></td>' +
                '<td>' + esc(client.alias || '—') + '</td>' +
                '<td>' + esc(client.screen || '—') + '</td>' +
                '<td><code>' + esc(client.ip) + '</code></td>' +
                '<td class="last-seen" data-last-seen="' + esc(client.last_seen) + '">' +
                    esc(relTime(client.last_seen)) + '</td>' +
                '<td>' + action + '</td>';

            body.appendChild(tr);
        });

        const count = document.getElementById('client-count');
        if (count) {
            count.textContent = clients.length;
        }
        const empty = document.getElementById('no-clients');
        if (empty) {
            empty.classList.toggle('d-none', clients.length > 0);
        }
    }

    function updateRelativeTimes() {
        document.querySelectorAll('.last-seen').forEach(function(el) {
            const iso = el.getAttribute('data-last-seen');
            if (iso) {
                el.textContent = relTime(iso);
            }
        });
    }

    function setLiveError(visible) {
        const el = document.getElementById('clients-error');
        if (el) {
            el.classList.toggle('d-none', !visible);
        }
    }

    function loadClients() {
        fetch(window.CLIENTS_URL, {cache: 'no-store', credentials: 'same-origin'})
            .then(function(response) {
                return response.ok ? response.json() : null;
            })
            .then(function(data) {
                if (data && data.clients) {
                    render(data.clients);
                    setLiveError(false);
                } else {
                    setLiveError(true);
                }
            })
            .catch(function() {
                // Transient failure; the next tick will retry.  Warn the
                // admin so an ageing "last seen" isn't mistaken for the truth.
                setLiveError(true);
            });
    }

    function refreshTarget(target, button) {
        if (button) {
            button.disabled = true;
        }
        $.post(window.CLIENTS_REFRESH_URL, {target: target}, function() {
            showToast('Refresh requested for ' +
                      (target === 'all' ? 'all clients' : target) + '.', 'success');
        }).fail(function() {
            showToast('Could not request refresh.', 'error');
        }).always(function() {
            if (button) {
                button.disabled = false;
            }
        });
    }

    $(function() {
        $('#refresh-all').on('click', function() {
            refreshTarget('all', this);
        });

        $('#clients-table').on('click', '.refresh-client', function() {
            refreshTarget(this.closest('tr').dataset.target, this);
        });

        loadClients();
        setInterval(loadClients, 5000);
        setInterval(updateRelativeTimes, 1000);
    });
})();