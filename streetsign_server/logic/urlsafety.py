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
'''
=====================================
streetsign_server.logic.urlsafety
=====================================

Validation helpers to guard server-side URL fetches against SSRF.

StreetSign fetches some URLs server-side (RSS feeds, externally-hosted
images). Without restriction these are SSRF sinks - an admin (or anyone who
can ride an admin session via CSRF) could point the server at internal
services (e.g. cloud metadata at 169.254.169.254), at localhost, or at
local files via file://. These helpers restrict such fetches to http(s)
URLs that resolve to public addresses.

'''

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURL(ValueError):
    ''' Raised when a URL is not safe to fetch server-side. '''


# Schemes we will fetch over the network. Deliberately excludes file://,
# ftp://, gopher://, dict://, etc.
ALLOWED_SCHEMES = ('http', 'https')


def _addr_is_private(addr):
    ''' Is this ip address one we must never let the server connect to? '''
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        # not an IP literal - can't decide here.
        return False
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_multicast or ip.is_reserved or ip.is_unspecified)


def check_fetch_url(url, resolve=True):
    ''' Raise UnsafeURL if `url` is not safe to fetch from the server.

        Checks the scheme is http(s), that there is a hostname, and (when
        `resolve` is True) that the hostname does not resolve to a private,
        loopback, or link-local address. Returns the url unchanged if OK. '''

    if not url or not isinstance(url, str):
        raise UnsafeURL('No URL supplied.')

    parsed = urlparse(url.strip())

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURL(
            f'URL scheme {parsed.scheme!r} is not allowed '
            f'(only {", ".join(ALLOWED_SCHEMES)}).')

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURL('URL has no hostname.')

    # block obvious internal hostnames outright.
    if hostname.lower() in ('localhost',):
        raise UnsafeURL('Refusing to fetch from localhost.')

    # if the host is an IP literal, check it directly.
    if _addr_is_private(hostname):
        raise UnsafeURL(f'Refusing to fetch from internal address {hostname}.')

    if resolve:
        try:
            infos = socket.getaddrinfo(hostname, parsed.port or None)
        except socket.gaierror as exc:
            raise UnsafeURL(f'Could not resolve host {hostname!r}.') from exc

        for info in infos:
            addr = info[4][0]
            if _addr_is_private(addr):
                raise UnsafeURL(
                    f'Host {hostname!r} resolves to internal address {addr}.')

    return url
