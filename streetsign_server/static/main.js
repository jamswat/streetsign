/*jslint browser:true, regexp: true, debug: true */
/*global $, jLater, confirm, alert */
'use strict';

////////////////////////////////////////////////
// CSRF token auto-injection for AJAX requests:

$(() => {
    const token = $('meta[name="csrf-token"]').attr('content');
    $(document).ajaxSend((event, xhr, settings) => {
        if (settings.type && settings.type.toUpperCase() !== 'GET') {
            if (settings.data instanceof FormData) {
                settings.data.append('_csrf_token', token);
            } else {
                settings.data = settings.data || '';
                settings.data += (settings.data ? '&' : '') + '_csrf_token=' + encodeURIComponent(token);
            }
        }
    });
});

////////////////////////////////////////////////
// Flashed notices:

$('#flashed_notices').children('li').click(function() {
    $(this).fadeOut();
});
setTimeout(() => { $('#flashed_notices > li').fadeOut('slow'); }, 15000);

function flash(text) {
    $('#flashed_notices').append($(`<li>${text} </li>`).click(function() { $(this).fadeOut(); }));
}

////////////////////////////////////////////////
// Nice select boxes:

$('select.chosen').each(function() {
    new Choices(this, { searchEnabled: true, itemSelectText: '', shouldSort: false });
});

/* Confirmation buttons: */

$('.confirm_delete').click(function() {
    return confirm('Really delete?');
});

$('a.confirm_ajax_delete').click(function(evt) {
    const dom_item = $(this).parents('*[data-item]');

    evt.preventDefault();

    if (confirm('Really delete?')) {
        dom_item.slideUp();
        $.ajax({
            url: $(dom_item).data('item'),
            type: 'DELETE'
        }).done(function(resp) {
            dom_item.slideUp('fast', dom_item.remove);
            flash('deleted');
        }).fail(function() {
            dom_item.slideDown();
            flash('could not delete!');
        });
    }
});

$('.popup_ask').click(function(evt) {
    const input = $(this.form).find(`input[name="${$(this).data('inputname')}"]`);
    const value = prompt($(this).data('prompt'), $(this).data('autofill'));

    if (value) {
        input.val(value);
    } else {
        evt.preventDefault();
    }
});

// focus on username input box when 'login' clicked.
$('#user_login_button').click(() => {
    setTimeout(() => { $('input[name="username"]').focus(); }, 500);
});

// hide expired posts, unless localStorage says don't.

if (localStorage.getItem('show_past_posts') === 'true') {
    $('.time_past').show();
    $('#show_past_posts').addClass('active');
} else {
    $('.time_past').hide();
}

$('#show_past_posts').click(function() {
    $('.time_past').toggle();
    $(this).toggleClass('active');
    localStorage.setItem('show_past_posts',
        localStorage.getItem('show_past_posts') === 'true' ? 'false' : 'true');
});

$('#run_housekeeping').click(function() {
    $.post(window.HOUSEKEEPING_URL, {}, function(data) {
        alert(`Housekeeping Done!\n${data.archived} posts archived.\n${data.deleted} posts deleted`);
    }, 'json');
});

// and run any js which was inserted by a template, which needs jQuery.

while (jLater.length) {
    jLater.pop()($);
}

////////////////////////////////

$(document).on('click', '.item_ajax_toggle', function() {
    const toggle_class = $(this).data('ajaxtoggle');
    const item = $(this).parents('.item').first().toggleClass(toggle_class);
    const data = {};

    data[$(this).data('name')] = $(this).data('value');

    $.ajax($(this).parents('[data-uri]').data('uri'), {
        type: $(this).data('ajaxtype'),
        data: data
    }).fail(function() {
        item.toggleClass(toggle_class);
        alert('Request failed — check your permissions.');
    });
});

$(() => {
    $('.autopost').change(function() {
        $.post(this.form.getAttribute('action'), $(this.form).serialize(), function(data) {
            if (data.message) {
                flash(data.message);
            } else {
                flash(data);
            }
        });
    });
});
