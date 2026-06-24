#!/bin/bash

if command -v magick &> /dev/null; then
    magick "$1" -resize 75x "$2"
else
    convert "$1" -resize 75x "$2"
fi
