#!/bin/bash

if command -v magick &> /dev/null; then
    magick "$1" -resize 1280x\> "$1"
else
    convert "$1" -resize 1280x\> "$1"
fi

exit $?
