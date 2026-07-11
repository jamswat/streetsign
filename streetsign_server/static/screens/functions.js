/************************************************************

    StreetSign Digital Signage Project
     (C) Copyright 2013 Daniel Fairhead

    StreetSign is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    StreetSign is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with StreetSign.  If not, see <http://www.gnu.org/licenses/>.

    ---------------------------------
    screens output, generic-ish functions.

*************************************************************/
function debug() {
    console.log(Array.prototype.slice.call(arguments));
}

function nicemap(objects, func) {
    'use strict';
    let i = objects.length;
    const runner = function() {
        if (i--) {
            func(objects[i]);
            requestAnimationFrame(runner);
        }
    };
    requestAnimationFrame(runner);
}

function safeGetJSON(url, callback, retry_time) {
    'use strict';
    retry_time = retry_time ?? 60000;

    const xhr = new XMLHttpRequest();
    const responder = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        callback(JSON.parse(xhr.responseText));
                    } catch (e) {
                        console.log(`Failed to parse response from ${url}. Trying again in ${retry_time / 1000} seconds`);
                        console.log(e);
                        setTimeout(() => { safeGetJSON(url, callback, retry_time); }, retry_time);
                    }
                } else {
                    console.log(`Failed to get ${url} successfully. Trying again in ${retry_time / 1000} seconds.`);
                    setTimeout(() => { safeGetJSON(url, callback, retry_time); }, retry_time);
                }
            }
        };

    if (callback) {
        xhr.onreadystatechange = responder;
    }
    xhr.ontimeout = () => {
        console.log('timeout.');
        setTimeout(() => { safeGetJSON(url, callback, retry_time); }, retry_time);
    };
    xhr.timeout = 10000;
    xhr.open('GET', url, true);
    xhr.send(null);
}

function reloadWhenThisURLContentChanges() {
    'use strict';
    let current_text = '';
    const reloader = function() {
        $.get(document.location.href, function(new_text) {
            if (new_text !== current_text) {
                document.location.reload(true);
            }
        });
    };

    $.get(document.location.href, function(first_text) {
        current_text = first_text;
        setInterval(reloader, 120000);
    });
}

function magic_vars(text) {
    'use strict';
    return text.replace(/%%TIME(.*?)%%/, '<span class="magic_time" data-format="$1">&nbsp;</span>')
               .replace(/%%DATE(.*?)%%/, '<span class="magic_date" data-format="$1">&nbsp;</span>');
}

function fill_magic_vars(root) {
    // Fill any magic_time / magic_date spans with their current values.
    // `root` is an optional DOM element / jQuery selector to scope the fill
    // (e.g. a single post). Defaults to the whole document.
    const d = dayjs();
    const $time = root ? $(root).find('.magic_time') : $('.magic_time');
    const $date = root ? $(root).find('.magic_date') : $('.magic_date');

    $time.each(function() {
        const format = $(this).data('format') || 'HH:mm';
        this.innerHTML = d.format(format);
    });
    $date.each(function() {
        const format = $(this).data('format') || 'YYYY-MM-DD';
        this.innerHTML = d.format(format);
    });
}

function magic_time() {
    fill_magic_vars();
    setTimeout(magic_time, 60000);
}

function url_insert(url, data) {
    'use strict';
    return url.replace(/-1/, data);
}

function faketime(timestring) {
    'use strict';
    if (timestring) {
        const split = timestring.match(/(\d\d):(\d\d)/);
        if (split && split.hasOwnProperty('length') && split.length === 3) {
            return (60 * parseInt(split[1])) + parseInt(split[2]);
        }
        console.log('invalid time: ' + JSON.stringify(timestring));
        return 0;
    }
    const now = new Date();
    return (60 * now.getHours()) + now.getMinutes();
}

function restriction_relevant(now, restriction) {
    'use strict';
    const start = faketime(restriction.start);
    const end = faketime(restriction.end);
    return start < now && now < end;
}

function any_relevent_restrictions(post) {
    'use strict';
    const now = faketime();
    let any_hits = post.time_restrictions_show;

    for (let i = 0; i < post.time_restrictions.length; i++) {
        if (restriction_relevant(now, post.time_restrictions[i])) {
            any_hits = !post.time_restrictions_show;
        }
    }

    return any_hits;
}

function reload_page() {
    'use strict';
    $.get(document.URL, () => { window.location.reload(); });
}

function reduce_font_size_to_fit(inner, outer) {
    'use strict';
    let percent = 100;
    const zone_height = $(outer).height();
    let zone_width = $(outer).width();
    let i = 100;
    const scrolling = outer[0].className.indexOf('scroll') !== -1;
    const img_sizes = {};

    if (scrolling) {
        zone_width = 900000;
    }

    $(inner).find('img').each(function(idx, img) {
        const $img = $(img);
        const w = $img.attr('width');
        const h = $img.attr('height');
        if (w && h) {
            img_sizes[idx] = { 'width%': parseFloat(w) / 100,
                               'height%': parseFloat(h) / 100 };
        }
    });

    while (i > 1) {
        const height = inner.height();
        const width = inner.width();

        i = i / 2;
        if ((height < zone_height - 5) || ((!scrolling) && (width < zone_width - 5))) {
            percent += i;
        } else if ((height > zone_height + 5) || ((!scrolling) && (width > zone_width + 5))) {
            percent -= i;
        }

        inner.css('font-size', percent + '%');
        inner.find('img').each(function(idx, img) {
            const $img = $(img);
            if (img_sizes[idx]) {
                $img.attr('width', img_sizes[idx]['width%'] * percent);
                $img.attr('height', img_sizes[idx]['height%'] * percent);
            }
        });
    }
    inner.css('font-size', parseInt(percent) + '%');
    console.log('reducing font size to ' + parseInt(percent) + '%');
}

function get_servertime(url) {
    const xhr = new XMLHttpRequest();
    url = url || document.location;
    xhr.open('GET', url, false);
    xhr.send(null);
    return new Date(xhr.getResponseHeader('Date'));
}

setInterval(reload_page, REFRESH_PAGE_TIMER);
magic_time();
