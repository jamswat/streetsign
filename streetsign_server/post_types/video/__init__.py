# -*- coding: utf-8 -*-
#  StreetSign Digital Signage Project
#     (C) Copyright 2013 Daniel Fairhead
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
"""
-----------------------------------
streetsign_server.post_types.video
-----------------------------------

HTML5 video post type.  Upload a video file to be displayed on screen.

"""

__NAME__ = 'Video'
__DESC__ = 'HTML5 video - upload a video file for screen display'

from os import makedirs, remove
from os.path import splitext, isdir, abspath, dirname, basename
from os.path import join as pathjoin
from uuid import uuid4

from flask import render_template_string, request, g, flash
from werkzeug.utils import secure_filename

from streetsign_server.post_types import my


def video_path():
    ''' Return the path to save videos to, creating the folder if needed. '''
    where = pathjoin(g.site_vars['user_dir'], 'post_videos')
    if not isdir(where):
        makedirs(where)
    return where


def allow_filetype(filename):
    ''' What video file types do we allow? '''
    return splitext(filename)[-1].lower() in (
        '.mp4', '.webm', '.ogg', '.ogv', '.mov'
    )


def form(data):
    """Form for editing a video post."""
    return render_template_string(my('form.html'), **data)


def receive(data):
    ''' Receive the form data, save the uploaded video, return saved info. '''

    if 'upload' in data:
        f = request.files['video_file']
        if f and allow_filetype(f.filename):
            filename = secure_filename(str(uuid4()) + basename(f.filename))
            full_path = pathjoin(video_path(), filename)
            f.save(full_path)
            flash('Video uploaded')
        else:
            raise IOError('Invalid file type. Allowed: .mp4, .webm, .ogg, .mov')
    else:
        filename = data.get('filename')
        if filename and allow_filetype(filename):
            filename = secure_filename(filename)
        else:
            raise Exception('Invalid filename')

    audio_enabled = data.get('audio_enabled', False) in (
        True, 'true', 'True', '1', 'on', 'checked'
    )

    return {
        'content': filename,
        'filename': filename,
        'file_url': g.site_vars['user_url'] + '/post_videos/' + filename,
        'audio_enabled': audio_enabled,
    }


def display(data):
    ''' Return HTML for backend preview of the video. '''
    return (
        f'<video controls style="width:100%;max-height:200px"'
        f' src="{data["file_url"]}"></video>'
    )


def screen_js():
    ''' Return the JavaScript for rendering this post on screen. '''
    return my('screen.js')


def delete(data):
    ''' Clean up the video file when the post is deleted. '''
    remove(pathjoin(video_path(), secure_filename(data['filename'])))
