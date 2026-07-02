#!/bin/bash
set -e

if command -v magick &> /dev/null; then
    IM=magick
elif command -v convert &> /dev/null; then
    IM=convert
else
    echo "makesmall: neither magick nor convert found" >&2
    exit 1
fi

# write to a temp file and rename atomically on success —
# prevents corrupting the original if ImageMagick crashes mid-write.
tmp=$(mktemp -t makesmall.XXXXXXXXXX)
$IM "$1" -resize 1280x\> "$tmp"
mv "$tmp" "$1"
