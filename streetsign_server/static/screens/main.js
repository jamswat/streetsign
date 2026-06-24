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
    screens output, main javascript control system.

*************************************************************/
'use strict';

function cssPairs(cssText) {
    try {
        return cssText.split(/[\n;]+/).map(function(x) {
            const y = x.match(/^(.*):(.*)$/);
            return [y[1].trim(), y[2].trim()];
        });
    } catch (e) {
        if (cssText) {
            console.log('invalid CSS!');
        }
        return [];
    }
}

function background_from_value(text) {
    if (text.indexOf('.') === -1) {
        return text;
    }
    return `url(/static/user_files/${text})`;
}

///////////////////////////////////////////////////////////////////////////////

function Zone(container, initial_data) {
    const that = this;
    const update = function(name, type) {
        if (initial_data.hasOwnProperty(name)) {
            try {
                that[name] = type(initial_data[name]);
            } catch (ignore) {
                that[name] = initial_data[name];
            }
        }
    };

    this.feeds = [];
    this.posts = [];
    this.next_posts = [];
    this.update_cb = make_updater(this);

    update('feeds');
    update('color');
    update('name');
    update('type', String);
    update('fontfamily');

    if (window.LOCALOPTS.hasOwnProperty('fadetime')) {
        this.fadetime = parseInt(window.LOCALOPTS.fadetime, 10);
    } else {
        this.fadetime = typeof initial_data.fadetime === 'string'
                          ? parseInt(initial_data.fadetime, 10)
                          : initial_data.fadetime || 500;
    }

    this.feedsurl = url_insert(window.POSTS_URL, JSON.stringify(this.feeds));

    console.log(this.type);

    this.el = $(zone_html(initial_data.name,
                          initial_data.top,
                          initial_data.left,
                          initial_data.bottom,
                          initial_data.right,
                          initial_data.css,
                          initial_data.type)).prependTo(container)[0];

    this.height = this.el.offsetHeight;
    this.width = this.el.scrollWidth;

    $(this.el).css('font-size', $(this.el).height() + 'px');
    $(this.el).css('color', that.color);
    if (that.fontfamily) {
        $(this.el).css('font-family', that.fontfamily);
    }
}

Zone.prototype = {
    type: 'fade',
    color: 'white',
    post_time: 4000,
    fadetime: 500,
    update_zones_timer: 10000,
    no_posts_wait: 10000,
    current_post: false,
    current_post_index: -1,

    addPost(new_data) {
        new_data.zone = this;
        new_data.el = post_types[new_data.type].render(this.el, new_data)[0];
        new_data.width = new_data.el.scrollWidth;
        new_data.height = new_data.el.scrollHeight;

        new_data.el.style.transition = `opacity 0.${this.fadetime}s`;
        this.posts.push(new_data);
    },

    delPost(index) {
        // no-op for now
    },

    updatePost(post, newData) {
        const that = this;

        post.time_restrictions_show = newData.time_restrictions_show;
        post.time_restrictions = newData.time_restrictions;

        if (post.changed !== newData.changed) {
            post.content = newData.content;

            if (this.current_post.id === post.id) {
                that.el.style.opacity = 0;
                setTimeout(() => {
                    const old_opacity = $(post.el).css('opacity');
                    console.log('replacing content in live post');
                    post.el.remove();
                    post.el = post_render(post, that);
                    post.width = post.el.scrollWidth;
                    post.height = post.el.offsetHeight;
                    $(post.el).css('opacity', old_opacity);
                    that.el.style.opacity = 1;
                }, 1000);
            } else {
                console.log(`replacing content in post:${post.id}`);
                post.el.remove();
                post.el = post_render(post, that);
            }

            post.changed = newData.changed;
        }

        if (this.type === 'fade') {
            post.display_time = newData.display_time;
            if (post === this.current_post && this.next_post_timer) {
                clearTimeout(this.next_post_timer);
                if (newData.display_time > 0) {
                    this.next_post_timer = setTimeout(
                        this.postTimeFinished.bind(this), newData.display_time
                    );
                }
            }
        }
    },

    showPost(post, after_cb) {
        const that = this;

        if (this.current_post === false) {
            this.current_post = post;
            post_fadein(this.current_post, after_cb);
            post_display(post);
            return;
        }

        if (post.id === this.current_post.id) {
            if (this.type === 'scroll') {
                post_fadeout(post, () => { post_fadein(post, after_cb); });
            } else {
                after_cb();
            }
            return;
        }

        post_fadeout(this.current_post, () => {
            post_hide(that.current_post);
            that.current_post = post;
            post_fadein(that.current_post, after_cb);
            post_display(post);
        });
    },

    findNextPost(already_gone_once) {
        const make_removeel = (post) => () => {
            post && post.hasOwnProperty('el') && post.el.remove();
        };

        for (let index = this.current_post_index - 1, i = 0;
             index !== this.current_post_index && i < this.posts.length;
             index -= 1, i++) {

            if (index < 0) {
                if (this.posts.length === 0) {
                    return undefined;
                }
                index = this.posts.length - 1;
            }

            let thispost = this.posts[index];

            if (!thispost) {
                continue;
            }

            if (thispost.hasOwnProperty('delete_me')) {
                console.log(`${this.name}|dropping post from feed (and removing el):${thispost.id}`);
                post_fadeout(thispost, make_removeel(this.posts.splice(index, 1)));

                if (this.current_post_index > index) {
                    this.current_post_index -= 1;
                }
                continue;
            }

            if (!any_relevent_restrictions(thispost)) {
                this.current_post_index = index;
                return thispost;
            } else if (this.current_post_index === index) {
                console.log('current post has time restriction! fading out...');
                post_fadeout(thispost);
                this.current_post_index = -1;
                this.current_post = false;
            }
        }

        return this.current_post;
    },

    postTimeFinished() {
        const that = this;
        const call_me_again = () => { that.postTimeFinished(); };

        if (that.posts.length === 0) {
            this.current_post = false;
            setTimeout(call_me_again, this.no_posts_wait);
            console.log(`no posts for ${this.name}!`);
            return;
        }

        const nextpost = this.findNextPost();

        if (nextpost) {
            that.showPost(nextpost, () => {
                if (nextpost.display_time === 0) {
                    return;
                }
                that.next_post_timer = setTimeout(call_me_again, nextpost.display_time);
            });
            return;
        }

        if (that.current_post) {
            post_fadeout(that.current_post, () => {
                if (!that.current_post) {
                    console.log('gone!');
                    return;
                }
                post_hide(that.current_post);
            });
        }

        that.current_post = false;
        that.next_post_timer = setTimeout(call_me_again, that.no_posts_wait);
        console.log(`no posts currently valid in ${that.name}!`);
    },

    pollForNewPosts(delay) {
        const that = this;

        safeGetJSON(this.feedsurl, (data) => {
            that.update_cb(data);
            setTimeout(() => { that.pollForNewPosts(); },
                       delay || that.update_zones_timer);
        });
    }
};

//////////////////////////////////////////////////////////////////////////////

function StreetScreen(element, initial_data) {
    const that = this;
    const forceaspect = window.LOCALOPTS.forceaspect;
    const windowheight = $('#zones').height();
    let newheight, newtop;

    this.zones = [];
    this.el = element;

    $(element).css('background-image',
                   background_from_value(initial_data.background));

    if (forceaspect !== undefined) {
        const ratio = parseFloat(forceaspect);
        if (ratio) {
            newheight = document.body.scrollWidth / ratio;
            $('#zones').height(newheight);
            newtop = parseInt(window.LOCALOPTS.forcetop, 10);
            if (isNaN(newtop)) {
                newtop = (windowheight - newheight) / 2;
            }
            $('#zones').css('top', newtop + 'px');
        }
    }

    this.id = initial_data.id;
    this.md5 = initial_data.md5;

    for (let i = 0; i < initial_data.zones.length; i += 1) {
        const zone = new Zone(this.el, initial_data.zones[i]);
        this.zones.push(zone);
        zone.pollForNewPosts(100 * i);
    }

    setTimeout(() => { that.update(); }, 3000);
}

StreetScreen.prototype = {
    background: 'black',
    css: '',
    md5: '12345',

    update() {
        const this_screen = this;
        const update_fn = function(data) {
            if (data.md5 === this_screen.md5) {
                setTimeout(() => { this_screen.update(); }, 50030);
            } else {
                reload_page();
            }
        };

        console.log('getting screen updates...');
        safeGetJSON(`/screens/json/${this_screen.id}/${this_screen.md5}`,
                    update_fn, 50000);
    },

    start_zones() {
        for (let i = 0; i < this.zones.length; i += 1) {
            this.zones[i].postTimeFinished();
        }
    }
};

//////////////////////////////////////////////////////////////////////////////

function make_updater(zone) {
    const do_next_post = () => { zone.postTimeFinished(); };

    const update_post = function(thiszone, post, data) {
        safeGetJSON(data.uri, (x) => { thiszone.updatePost(post, x); });
    };

    const new_post_ids = {};
    const current_post_ids = [];
    const posts_to_drop = [];

    if (!zone.hasOwnProperty('posts')) { zone.posts = []; }

    return function(data) {
        Object.keys(new_post_ids).forEach(k => delete new_post_ids[k]);
        current_post_ids.length = 0;
        posts_to_drop.length = 0;

        let arrId = -1;

        for (let i = 0; i < data.posts.length; i += 1) {
            new_post_ids[data.posts[i].id] = i;
        }

        for (let i = 0; i < zone.posts.length; i += 1) {
            if (new_post_ids[zone.posts[i].id] !== undefined) {
                arrId = new_post_ids[zone.posts[i].id];
                current_post_ids.push(zone.posts[i].id);

                if (data.posts[arrId].changed !== zone.posts[i].changed) {
                    update_post(zone, zone.posts[i], data.posts[arrId]);
                }
            } else {
                console.log(`marking post for delete:${zone.posts[i].id}`);
                zone.posts[i].delete_me = true;

                if (zone.current_post === zone.posts[i]) {
                    console.log(`${zone.name}|bringing forward next post timer`);
                    clearTimeout(zone.next_post_timer);
                    zone.next_post_timer = setTimeout(do_next_post, 1000);
                } else {
                    console.log(`${zone.name}|adding to dropqueue:${zone.posts[i].id}`);
                    posts_to_drop.push(i);
                }
            }
        }

        posts_to_drop.sort().reverse();

        for (let i = 0; i < posts_to_drop.length; i += 1) {
            zone.posts.splice(posts_to_drop[i], 1);
        }

        for (let i = 0; i < data.posts.length; i += 1) {
            if (current_post_ids.indexOf(data.posts[i].id) === -1) {
                safeGetJSON(data.posts[i].uri, (x) => { zone.addPost(x); });
            }
        }
    };
}
