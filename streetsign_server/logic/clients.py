# -*- coding: utf-8 -*-
#  StreetSign Digital Signage Project
#     (C) Copyright 2013-2026 Daniel Fairhead
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
#    -------------------------------
"""
---------------------------------------
streetsign_server.logic.clients
---------------------------------------

Tracks connected display clients and provides a "force refresh" command
channel.

Display screens are anonymous browsers that poll the server for content.  They
send a lightweight heartbeat (see ``static/screens/heartbeat.js``) which
registers their IP address against the screen/alias they are showing.  Admins
can bump a per-target refresh counter which the heartbeat hands back to the
client, causing it to reload.

Presence and refresh state are ephemeral and process-local, which matches the
single-process waitress deployment (see ``run.py``).  Nothing here is used for
authentication.
"""

from datetime import timedelta
from ipaddress import ip_address
from threading import Lock
from uuid import uuid4

from streetsign_server import app
from streetsign_server.models import now

# Random per-process id.  Clients reload once when it changes, so that a
# server restart refreshes every connected screen.
_BOOT_ID = uuid4().hex

_lock = Lock()

# (alias-or-screen, ip) -> {screen_id, screen, alias, ip, user_agent, last_seen}
_presence = {}

# refresh target ("all", "alias:<name>", "screen:<urlname>") -> int
_refresh = {'all': 0}

# Hard cap on presence entries, so a flood of spoofed heartbeats (e.g. with
# forged X-Forwarded-For values) cannot grow memory without bound.
_MAX_PRESENCE = 2000

# Length caps on the attacker-influenced values stored per client.  The
# heartbeat is public, so without these an oversized header could bloat memory.
_MAX_IP_LEN = 45            # longest textual IPv6 address
_MAX_ALIAS_LEN = 200
_MAX_USER_AGENT_LEN = 300


def _safe_ip(value):
    """Return *value* normalised if it is a valid IP address, else ``None``.

    This both rejects junk and bounds the length of anything we store.
    """
    if not value or len(value) > _MAX_IP_LEN:
        return None
    try:
        return str(ip_address(value))
    except ValueError:
        return None


def client_ip(request):
    """Best-effort real client IP for *request*.

    Display clients are commonly reached through a reverse proxy (nginx,
    Docker), so ``request.remote_addr`` is the proxy.  ``X-Forwarded-For`` is
    honoured according to the ``TRUST_PROXY_HEADERS`` config value:

    - ``'auto'`` (default): only trust it when the immediate peer is a
      loopback or private address, i.e. a local/reverse proxy.
    - ``True``: always trust it.
    - ``False``: never trust it.

    The *left-most* X-Forwarded-For entry is used: that is the address of the
    originating client, which is what an admin wants to see even when the
    request passes through several proxies (each of which appends its own
    address to the right).  The value must be a syntactically valid IP,
    otherwise we fall back to the socket peer.

    Because a client controls the left-hand entries, a client can forge the
    address shown here if an upstream proxy forwards its X-Forwarded-For
    header unchanged.  That is acceptable because this value is informational
    only — it is never used for authentication or rate limiting.
    """
    peer = request.remote_addr or ''
    trust = app.config.get('TRUST_PROXY_HEADERS', 'auto')

    if trust is False:
        return peer
    if trust is not True and not _is_trusted_peer(peer):
        return peer

    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        candidate = _safe_ip(forwarded.split(',')[0].strip())
        if candidate:
            return candidate
    return peer


def _is_trusted_peer(peer):
    """True if *peer* is a loopback or private (RFC1918/ULA) address."""
    try:
        address = ip_address(peer)
    except ValueError:
        return False
    return address.is_loopback or address.is_private


def _valid_target(target):
    """Return True if *target* is a refresh target we understand."""
    if target == 'all':
        return True
    if target.startswith('alias:') or target.startswith('screen:'):
        return bool(target.split(':', 1)[1])
    return False


def record_heartbeat(screen_id, screen_name, alias, ip, user_agent):
    """Register a display client as connected and return its refresh state.

    Returns a dict suitable for sending straight back to the client.
    """
    alias = (alias or '')[:_MAX_ALIAS_LEN] or None
    user_agent = (user_agent or '')[:_MAX_USER_AGENT_LEN]
    ip = _safe_ip(ip) or (ip or '')[:_MAX_IP_LEN]

    key = (alias or screen_name or f'screen:{screen_id}', ip)

    with _lock:
        _purge_stale()
        _presence[key] = {
            'screen_id': screen_id,
            'screen': screen_name,
            'alias': alias,
            'ip': ip,
            'user_agent': user_agent,
            'last_seen': now(),
        }
        refresh = _refresh_state(screen_name, alias)

    return {
        'refresh': refresh,
        'server': _BOOT_ID,
        'interval': app.config.get('SCREEN_HEARTBEAT_INTERVAL', 10),
    }


def _refresh_state(screen_name, alias):
    """Sum of every refresh counter that applies to this client.

    Counters only ever increase, so any change means "please reload".
    """
    total = _refresh.get('all', 0)
    if screen_name:
        total += _refresh.get(f'screen:{screen_name}', 0)
    if alias:
        total += _refresh.get(f'alias:{alias}', 0)
    return total


def _purge_stale():
    """Drop presence entries older than the TTL, then enforce the hard cap.

    Caller must hold ``_lock``.
    """
    ttl = app.config.get('SCREEN_CLIENT_TTL', 30)
    cutoff = now() - timedelta(seconds=ttl)

    for key in [k for k, v in _presence.items() if v['last_seen'] < cutoff]:
        del _presence[key]

    overflow = len(_presence) - _MAX_PRESENCE
    if overflow > 0:
        oldest = sorted(_presence, key=lambda k: _presence[k]['last_seen'])
        for key in oldest[:overflow]:
            del _presence[key]


def connected_clients():
    """Return the list of clients seen within ``SCREEN_CLIENT_TTL`` seconds.

    Stale entries are purged as a side effect.  Each item is a plain dict with
    an ISO formatted ``last_seen`` timestamp, ready to be JSON serialised.
    """
    with _lock:
        _purge_stale()
        items = list(_presence.values())

    items.sort(key=lambda c: ((c['alias'] or c['screen'] or ''), c['ip']))

    return [
        {
            'screen_id': c['screen_id'],
            'screen': c['screen'],
            'alias': c['alias'],
            'ip': c['ip'],
            'user_agent': c['user_agent'],
            'last_seen': c['last_seen'].astimezone()
                                  .isoformat(timespec='seconds'),
        }
        for c in items
    ]


def request_refresh(target='all'):
    """Bump the refresh counter for *target*, forcing matching clients to
    reload on their next heartbeat.  Returns the new counter value.

    Raises ``ValueError`` for an unrecognised target.
    """
    if not _valid_target(target):
        raise ValueError(f'invalid refresh target: {target!r}')

    with _lock:
        _refresh[target] = _refresh.get(target, 0) + 1
        return _refresh[target]


def reset():
    """Clear all presence and refresh state.  Used by tests."""
    with _lock:
        _presence.clear()
        _refresh.clear()
        _refresh['all'] = 0
