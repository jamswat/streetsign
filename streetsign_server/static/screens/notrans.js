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
    screens output, JS transitions theme (notrans)
      zone HTML, post fade-in/out, scroll via requestAnimationFrame

*************************************************************/
'use strict';

const _mt = function() {};

function zone_html(id, top, left, bottom, right, css, type) {
    return `<div id="_zone_${id}" class="zone zone_${type}" style="`
            + `left:${left}`
            + `;right:${right}`
            + `;bottom:${bottom}`
            + `;top:${top}`
            + `;${css.replace(/"/g, "'")}`
            + `"></div>`;
}

const zone_types = {
    fade: {
        start(post, cb) {
            post.el.style.opacity = 1;
            setTimeout(cb, post.zone.fadetime);
        },
        stop(post, cb) {
            post.el.style.opacity = 0;
            setTimeout(() => { cb && cb(); }, post.zone.fadetime);
        }
    },
    scroll: {
        start(post, cb) {
            let stylesheet;

            if (!post.scroll_stylesheet) {
                fill_magic_vars(post.el);
                post.width = post.el.scrollWidth;

                stylesheet = document.createElement('style');
                stylesheet.appendChild(document.createTextNode(
                    `@keyframes slide_${post.id}`
                    + ` { from { transform: translateX(${post.zone.width}px) }`
                    + ` to { transform: translateX(-${post.width}px)}}`
                ));

                post.scroll_stylesheet = document.head.appendChild(stylesheet);
            }

            post.el.style.display = 'block';
            post.el.style.opacity = 0;
            post.display_time = (post.width + post.zone.width) * 14;

            post.el.style.opacity = '1';
            const css = `slide_${post.id} ${parseInt(post.display_time / 1000)}s linear 0s 1 both`;
            post.el.style.animation = css;

            cb && cb();
        },
        stop(post, cb) {
            post.zone.el.style.opacity = 0;

            setTimeout(() => {
                post.el.style.display = 'none';
                post.el.style.animation = '';
                post.el.style.opacity = 0;
                post.zone.el.style.opacity = 1;
                if (post.scroll_stylesheet && post.scroll_stylesheet.parentNode) {
                    post.scroll_stylesheet.parentNode.removeChild(post.scroll_stylesheet);
                }
                post.scroll_stylesheet = null;
                cb && cb();
            }, 1001);
        }
    }
};

function post_fadein(post, cb) {
    return (zone_types[post.zone.type] || zone_types.fade).start(post, cb);
}

function post_fadeout(post, cb) {
    return (zone_types[post.zone.type] || zone_types.fade).stop(post, cb);
}

function post_display(post) {
    if (post_types[post.type].hasOwnProperty('display')) {
        post_types[post.type].display(post);
    }
}

function post_hide(post) {
    if (post_types[post.type].hasOwnProperty('hide')) {
        post_types[post.type].hide(post);
    }
}

function post_render(post_data, zone) {
    return post_types[post_data.type].render(zone.el, post_data)[0];
}
