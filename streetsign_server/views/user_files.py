# -*- coding: utf-8 -*-
#    StreetSign Digital Signage Project
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
#    ---------------------------------

"""
    streetsign_server.views.user_files
    ----------------------------------

    Views for working with user-uploaded files.

"""


from glob import glob
import re
from os.path import basename, dirname, join as pathjoin, splitext, isdir, isfile, realpath
from os import makedirs, remove, stat, sep as ossep
from subprocess import run, CalledProcessError
from datetime import datetime

from flask import render_template, request, redirect, \
                  flash, g, url_for, Response
from markupsafe import Markup, escape
from werkzeug.utils import secure_filename # pylint: disable=no-name-in-module

from streetsign_server import user_session
from streetsign_server.views.utils import admin_only, registered_users_only
from streetsign_server import app

##################################################################
# user uploaded files:

def human_size_str(filename):
    ''' returns a human-readable size (string) of a file-name '''
    s = stat(filename).st_size
    if s > 1048576:
        return f'{s/1048576:.1f} MB'
    if s > 1024:
        return f'{s/1024:.0f} kB'
    return f'{s} B'

# TODO: move to file upload lib.


IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', '.avif']
FONT_EXTENSIONS = ['.ttf', '.otf', '.woff', '.woff2']
VIDEO_FORMATS = ['.mp4', '.webm', '.ogg', '.ogv', '.mov']
ALLOWED_FORMATS = IMAGE_FORMATS + FONT_EXTENSIONS + VIDEO_FORMATS

def allow_filetype(filename):
    ''' is this file-type allowed to be uploaded? '''
    return splitext(filename)[-1].lower() in ALLOWED_FORMATS

def make_dirlist(path):
    ''' returns a list of the files and sub-dirs in a directory, ready to be
        JSON encoded, and sent to a client, or rendererd server-side. '''

    return_list = []
    things = glob(pathjoin(g.site_vars['user_dir'], path, '*'))
    for f in things:
        name = basename(f)
        if isdir(f):
            return_list.append(
                {'name': name + '/',
                 'url':  name + '/',
                 'size': f"{len(glob(pathjoin(f, '*')))} items",
                 'is_dir': True})
        else:
            file_stat = stat(f)
            ext = splitext(name)[1].lower()
            if ext in IMAGE_FORMATS:
                safe_name = escape(name)
                thumb = Markup(
                    f'<img src="{url_for("thumbnail", filename=path + name)}"'
                    f' alt="{safe_name}" />')
                file_type = 'Image'
                font_family = ''
                font_preview_url = ''
            elif ext in FONT_EXTENSIONS:
                thumb = ('<i class="bi bi-file-earmark-font"'
                            ' style="font-size: 1.5rem;"'
                            ' title="Font file"></i> ')
                file_type = 'Font'
                font_name = re.sub(r'[^A-Za-z0-9 _-]', '', splitext(name)[0]).strip()
                font_family = font_name if font_name else name
                font_preview_url = url_for('static', filename='user_files/fonts/' + name)
            elif ext in VIDEO_FORMATS:
                thumb = ('<i class="bi bi-film"'
                            ' style="font-size: 1.5rem;"'
                            ' title="Video file"></i> ')
                file_type = 'Video'
                font_family = ''
                font_preview_url = ''
            else:
                thumb = ''
                file_type = 'Other'
                font_family = ''
                font_preview_url = ''

            mod_time = datetime.fromtimestamp(file_stat.st_mtime)

            return_list.append(locals_dict(name=name, thumb=thumb,
                url=pathjoin(g.site_vars['user_url'], path, name),
                size=human_size_str(f), size_raw=file_stat.st_size, is_dir=False,
                ext=ext, file_type=file_type, font_family=font_family,
                font_preview_url=font_preview_url,
                mod_time=mod_time.strftime('%Y-%m-%d %H:%M'),
                mod_time_raw=mod_time.isoformat(),
                mod_ts=mod_time.timestamp()))
    return return_list


def locals_dict(**kwargs):
    return kwargs

@app.route('/user_files/', methods=['GET', 'POST'])
@app.route('/user_files/<path:dir_name>', methods=['GET', 'POST'])
@admin_only('POST')
@registered_users_only('GET')
def user_files_list(dir_name=""):
    ''' HTML list of user-uploaded files. '''

    user = user_session.get_user()

    full_path = pathjoin(g.site_vars['user_dir'], dir_name)
    real_base = realpath(g.site_vars['user_dir'])
    real_path = realpath(full_path)
    if not real_path.startswith(real_base + ossep) and real_path != real_base:
        flash('Invalid path')
        return redirect(url_for('user_files_list'))

    if not isdir(full_path):
        # Only an admin POST (an actual upload/management action) may create
        # directories - a GET must never have filesystem side effects.
        if request.method == 'POST' and user.is_admin:
            makedirs(full_path)
        else:
            flash('No such directory')
            return redirect(url_for('user_files_list'))

    if request.method == 'POST' and user.is_admin:
        if request.form.get('action') == 'upload':
            f = request.files.get('file') or request.files.get('image_file')
            if f and allow_filetype(f.filename):
                filename = secure_filename(f.filename)
                ext = splitext(filename)[-1].lower()
                save_dir = full_path
                if ext in FONT_EXTENSIONS:
                    fonts_dir = pathjoin(g.site_vars['user_dir'], 'fonts')
                    if not isdir(fonts_dir):
                        makedirs(fonts_dir)
                    save_dir = fonts_dir
                elif ext in VIDEO_FORMATS:
                    videos_dir = pathjoin(g.site_vars['user_dir'], 'videos')
                    if not isdir(videos_dir):
                        makedirs(videos_dir)
                    save_dir = videos_dir
                f.save(pathjoin(save_dir, filename))
                flash('Uploaded file: ' + filename)
            else:
                flash('Sorry. Invalid Filetype')
        elif request.form.get('action') == 'delete':
            raw_filename = request.form.get('filename')
            if not raw_filename:
                flash('No filename supplied for deletion.')
            else:
                filename = secure_filename(raw_filename)
                full_filename = pathjoin(full_path, filename)
                if isfile(full_filename):
                    remove(full_filename)
                    try:
                        thumb_path = pathjoin(g.site_vars['user_dir'],
                                           '.thumbnails', dir_name,
                                           splitext(filename)[0] + '.png')
                        thumb_base = realpath(pathjoin(g.site_vars['user_dir'],
                                                       '.thumbnails'))
                        if realpath(thumb_path).startswith(thumb_base + ossep) \
                                and isfile(thumb_path):
                            remove(thumb_path)
                    except OSError:
                        pass
                    flash('Deleted ' + filename)
                else:
                    flash('Cannot delete directory: ' + filename)
        elif request.form.get('action') == 'delete_selected':
            filenames = request.form.getlist('filenames[]')
            deleted = 0
            for fname in filenames:
                fname = secure_filename(fname)
                full_filename = pathjoin(full_path, fname)
                if isfile(full_filename):
                    remove(full_filename)
                    try:
                        thumb_path = pathjoin(g.site_vars['user_dir'],
                                           '.thumbnails', dir_name,
                                           splitext(fname)[0] + '.png')
                        thumb_base = realpath(pathjoin(g.site_vars['user_dir'],
                                                       '.thumbnails'))
                        if realpath(thumb_path).startswith(thumb_base + ossep) \
                                and isfile(thumb_path):
                            remove(thumb_path)
                    except OSError:
                        pass
                    deleted += 1
            flash(f'Deleted {deleted} file(s)')


    files = make_dirlist(dir_name)

    dir_breadcrumbs = []
    parent_dir = None
    if dir_name:
        clean = dir_name.rstrip('/')
        parts = clean.split('/')
        acc = ''
        for i, part in enumerate(parts):
            acc = pathjoin(acc, part) if acc else part
            dir_breadcrumbs.append({
                'name': part,
                'url': url_for('user_files_list', dir_name=acc),
                'last': i == len(parts) - 1
            })
        parent_dir = clean.rsplit('/', 1)[0] if '/' in clean else ''

    return render_template('user_files.html',
                           full_path=full_path,
                           file_list=files,
                           dirname=dir_name,
                           dir_breadcrumbs=dir_breadcrumbs,
                           parent_dir=parent_dir,
                           breadcrumbs=[('Dashboard', url_for('index')),
                                        ('Uploaded Files', None)])

@app.route('/thumbnail/<path:filename>')
@registered_users_only('GET')
def thumbnail(filename):
    ''' return a thumbnail of an (image) file.  if one doesn't exist,
        create one (with imagemagick(convert)) '''

    full_path = pathjoin(g.site_vars['user_dir'], filename)
    thumb_name = splitext(filename)[0] + '.png'
    thumb_path = pathjoin(g.site_vars['user_dir'], '.thumbnails', thumb_name)
    real_base = realpath(g.site_vars['user_dir'])
    real_path = realpath(full_path)
    if not real_path.startswith(real_base + ossep) and real_path != real_base:
        flash('Invalid path')
        return redirect(url_for('user_files_list'))

    # the thumbnail target must also resolve under .thumbnails/
    thumb_base = realpath(pathjoin(g.site_vars['user_dir'], '.thumbnails'))
    if not realpath(thumb_path).startswith(thumb_base + ossep):
        flash('Invalid path')
        return redirect(url_for('user_files_list'))

    if splitext(filename)[-1].lower() not in IMAGE_FORMATS:
        return Response('not an image I will not make a thumbnail.', status=415)

    if not isfile(full_path):
        return Response('Sorry! not a valid original file!', status=404)

    if not isfile(thumb_path):
        where = pathjoin(g.site_vars['user_dir'],
                         '.thumbnails',
                         dirname(filename))
        if not isdir(where):
            makedirs(where)

        try:
            result = run([pathjoin(g.site_vars['site_dir'],
                                   'scripts',
                                   'makethumbnail.sh'),
                         full_path, thumb_path],
                         capture_output=True, text=True)
            result.check_returncode()
        except CalledProcessError:
            app.logger.error('thumbnail generation failed: %s\nstderr: %s',
                             full_path, result.stderr.strip())
            return Response('Sorry! Thumbnail generation failed.', status=500)
        except OSError as exc:
            app.logger.error('thumbnail generation failed: %s\nOSError: %s',
                             full_path, exc)
            return Response('Sorry! Thumbnail generation failed.', status=500)

    return redirect(g.site_vars['user_url'] + '/.thumbnails/' + thumb_name)

def user_fonts():
    ''' return a list of (name, url) tuples for all user-available fonts. 
    '''
    fonts = []
    for f in glob(app.config['SITE_VARS']['user_dir'] + 'fonts/*'):
        if splitext(f)[1].lower() in FONT_EXTENSIONS:
            name = splitext(basename(f))[0]
            url = url_for('static', filename='user_files/fonts/' + basename(f))
            fonts.append((name, url))
    return fonts


@app.route('/user_files/fonts.css')
def user_fonts_css():
    ''' return a CSS file with @font-face definitions for each font in the user
        uploaded fonts directory '''
    fonts = user_fonts()
    css_fonts = []
    fmt_map = {'.ttf': 'truetype', '.otf': 'opentype',
               '.woff': 'woff', '.woff2': 'woff2'}
    for name, url in fonts:
        # The font name derives from the uploaded filename - strip anything
        # that could break out of the CSS string/declaration (CSS injection).
        safe_name = re.sub(r'[^A-Za-z0-9 _-]', '', name).strip()
        if not safe_name:
            continue
        ext = splitext(url)[1].lower()
        fmt = fmt_map.get(ext, '')
        if fmt:
            css_fonts.append(
                '@font-face {font-family: "%s"; src:url("%s") format("%s")}'
                % (safe_name, url, fmt))
        else:
            css_fonts.append(
                '@font-face {font-family: "%s"; src:url("%s")}'
                % (safe_name, url))

    return Response('\n'.join(css_fonts), status=200, mimetype='text/css')
