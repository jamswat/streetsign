/*jslint browser:true, regexp: true, debug: true */
/*global $, jLater */
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
// AJAX loading progress bar:

$(() => {
    const $bar = $('#ajax-progress');
    let reqs = 0;

    $(document).ajaxStart(() => {
        reqs += 1;
        $bar.show();
    });

    $(document).ajaxStop(() => {
        reqs = Math.max(0, reqs - 1);
        if (reqs <= 0) {
            reqs = 0;
            $bar.fadeOut('fast');
        }
    });
});

////////////////////////////////////////////////
// Sidebar toggle for mobile:
$('#sidebar-toggle').click(function() {
    $('.sidebar').toggleClass('open');
    $('#sidebar-overlay').toggleClass('show');
    $('body').toggleClass('overflow-hidden');
});

$('#sidebar-overlay').click(function() {
    $('.sidebar').removeClass('open');
    $(this).removeClass('show');
    $('body').removeClass('overflow-hidden');
});

////////////////////////////////////////////////
// Dark mode toggle:

$(() => {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-bs-theme', theme);
    updateThemeIcon(theme);

    $('#theme-toggle').click(() => {
        const current = document.documentElement.getAttribute('data-bs-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-bs-theme', next);
        localStorage.setItem('theme', next);
        updateThemeIcon(next);
    });
});

function updateThemeIcon(theme) {
    const icon = $('#theme-toggle span.bi');
    icon.removeClass('bi-sun-fill bi-moon-stars-fill');
    icon.addClass(theme === 'dark' ? 'bi-sun-fill' : 'bi-moon-stars-fill');
}

////////////////////////////////////////////////
// Bootstrap toast helper:

function showToast(message, type) {
    type = type || 'info';
    const bgClass = {
        info: 'text-bg-secondary',
        success: 'text-bg-success',
        error: 'text-bg-danger',
        warning: 'text-bg-warning'
    }[type] || 'text-bg-secondary';

    const id = 'toast-' + Date.now();
    const toast = $(`
        <div id="${id}" class="toast align-items-center ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `);
    $('.toast-container').append(toast);
    const bsToast = new bootstrap.Toast(toast[0], { delay: 5000 });
    bsToast.show();
    toast.on('hidden.bs.toast', () => toast.remove());
}

////////////////////////////////////////////////
// Bootstrap confirm modal:

function confirmAction(message, onConfirm) {
    $('#confirm-modal-message').text(message || 'Are you sure?');
    const modal = new bootstrap.Modal('#confirm-modal');
    const okBtn = $('#confirm-modal-ok');

    okBtn.off('click').click(() => {
        modal.hide();
        if (onConfirm) { onConfirm(); }
    });

    modal.show();
}

////////////////////////////////////////////////
// Flashed notices (now rendered as toasts, see index.html):

// Loading indicators for AJAX:


$('select.chosen').each(function() {
    new Choices(this, { searchEnabled: true, itemSelectText: '', shouldSort: false });
});

/* Confirmation buttons: */

$('.confirm_delete').click(function(evt) {
    const form = this.form;
    evt.preventDefault();
    confirmAction('Really delete?', function() {
        form.submit();
    });
});

$('a.confirm_ajax_delete').click(function(evt) {
    const dom_item = $(this).parents('*[data-item]');

    evt.preventDefault();

    confirmAction('Really delete?', function() {
        dom_item.slideUp();
        $.ajax({
            url: $(dom_item).data('item'),
            type: 'DELETE'
        }).done(function(resp) {
            dom_item.slideUp('fast', dom_item.remove);
            showToast('Deleted successfully.', 'success');
        }).fail(function() {
            dom_item.slideDown();
            showToast('Could not delete!', 'error');
        });
    });
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
        showToast(
            'Housekeeping: ' + data.archived + ' archived, ' + data.deleted + ' deleted.',
            'success'
        );
    }, 'json');
});

// and run any js which was inserted by a template, which needs jQuery.

while (jLater.length) {
    jLater.pop()($);
}

////////////////////////////////

$(document).on('click', '.clickable-row', function(evt) {
    const tag = evt.target.tagName.toLowerCase();
    const isInteractive = tag === 'a' || tag === 'button' || tag === 'input' ||
                          tag === 'select' || tag === 'textarea' || tag === 'label';
    if (!isInteractive && !$(evt.target).closest('a, button, input, select, textarea, label').length) {
        window.location.href = $(this).data('uri');
    }
});

$(document).on('click', '.item_ajax_toggle', function(evt) {
    const btn = $(this);
    if (btn.attr('data-confirm') !== undefined) {
        evt.preventDefault();
        confirmAction('Really delete?', doToggle);
    } else {
        doToggle();
    }

    function doToggle() {
        const toggle_class = btn.data('ajaxtoggle');
        const item = btn.parents('.item').first().toggleClass(toggle_class);
        const data = {};

        data[btn.data('name')] = btn.data('value');

        $.ajax(btn.parents('[data-uri]').data('uri'), {
            type: btn.data('ajaxtype'),
            data: data
        }).fail(function() {
            item.toggleClass(toggle_class);
            showToast('Request failed — check your permissions.', 'error');
        });
    }
});

$(() => {
    $('.autopost').change(function() {
        $.post(this.form.getAttribute('action'), $(this.form).serialize(), function(data) {
            if (data.message) {
                showToast(data.message, 'success');
            } else {
                showToast(data, 'info');
            }
        });
    });

    $('form.needs-validation').on('submit', function(evt) {
        if (!this.checkValidity()) {
            evt.preventDefault();
            evt.stopPropagation();
        }
        $(this).addClass('was-validated');
    });
});
