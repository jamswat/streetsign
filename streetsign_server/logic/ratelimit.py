"""Simple in-memory IP-based rate limiter for login brute-force protection.

Tracks recent login attempts per IP address.  Complements the existing
per-user failed_logins / is_locked_out mechanism at the model layer.

Disabled automatically when Flask's TESTING config flag is set.
"""

import time
import threading

from streetsign_server import app

_MAX_ATTEMPTS = 5
_WINDOW = 60  # seconds

_lock = threading.Lock()
_attempts: dict[str, list[float]] = {}


def is_rate_limited(ip: str,
                    max_attempts: int = _MAX_ATTEMPTS,
                    window: int = _WINDOW) -> bool:
    """Return True if *ip* has exceeded *max_attempts* within *window* seconds.

    Each call registers an attempt for the given IP *before* checking the
    threshold, so callers should only invoke this after receiving a login
    POST, not before.
    """
    if app.config.get('TESTING'):
        return False

    now = time.time()
    cutoff = now - window

    with _lock:
        _cleanup(cutoff)

        timestamps = _attempts.get(ip)
        if timestamps is None:
            timestamps = []
            _attempts[ip] = timestamps

        timestamps.append(now)
        recent = [t for t in timestamps if t > cutoff]
        _attempts[ip] = recent

        return len(recent) > max_attempts


def _cleanup(cutoff: float):
    """Remove entries whose most recent timestamp is older than *cutoff*."""
    stale = [ip for ip, ts in _attempts.items()
             if not ts or ts[-1] <= cutoff]
    for ip in stale:
        del _attempts[ip]
