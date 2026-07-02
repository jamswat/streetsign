#!/bin/bash
set -e

if command -v magick &> /dev/null; then
    IM=magick
elif command -v convert &> /dev/null; then
    IM=convert
else
    echo "makethumbnail: neither magick nor convert found" >&2
    exit 1
fi

# always output PNG – some formats (AVIF, HEIC) can be read but
# not written back by ImageMagick, and PNG is universally supported.
$IM "$1" -auto-orient -strip -resize 75x "PNG:$2"
