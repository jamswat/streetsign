#!/bin/bash
# always output PNG – some formats (AVIF, HEIC) can be read but
# not written back by ImageMagick, and PNG is universally supported.
if command -v magick &> /dev/null; then
    magick "$1" -auto-orient -strip -resize 75x "PNG:$2"
else
    convert "$1" -auto-orient -strip -resize 75x "PNG:$2"
fi
