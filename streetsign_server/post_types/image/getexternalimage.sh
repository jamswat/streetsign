#!/bin/bash
# Fetch an external image. Defence-in-depth alongside the Python-side
# URL safety check (streetsign_server/logic/urlsafety.py):
#   --proto restricts to http/https (no file://, gopher://, dict://, ...)
#   --proto-redir keeps redirects on http/https only
#   --max-time / --max-filesize bound the request
#   -L follows redirects (still constrained by --proto-redir)
curl --proto '=http,https' \
     --proto-redir '=http,https' \
     --location \
     --max-redirs 5 \
     --max-time 30 \
     --max-filesize 104857600 \
     --silent --show-error \
     -- "$1" -o "$2"
exit $?
