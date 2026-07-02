/*global $, flatpickr */
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
    Post Times Editor - Alpine.js data factory

*************************************************************/
'use strict';

window.makeTimesEditor = function(initialTimes) {
    const times = (initialTimes || []).map(function(t) {
        return {
            start: t.start || '00:00',
            end: t.end || '23:59',
            note: t.note || ''
        };
    });

    return {
        times: times,

        get serializedTimes() {
            return JSON.stringify(this.times);
        },

        addTime() {
            this.times.push({ start: '00:00', end: '23:59', note: '' });
        },

        timeInvalid(idx) {
            var t = this.times[idx];
            return t.start && t.end && t.start >= t.end;
        },

        removeTime(idx) {
            this.times.splice(idx, 1);
        }
    };
};

// Date/time pickers for the main post start/end fields
flatpickr('#active_start', {
    enableTime: true,
    dateFormat: 'Y-m-d H:i:s',
    allowInput: true
});
flatpickr('#active_end', {
    enableTime: true,
    dateFormat: 'Y-m-d H:i:s',
    allowInput: true
});

// Make calendar icons clickable to open the picker
$('#datetimestart .bi-calendar').parent().on('click', function() {
    document.querySelector('#active_start')._flatpickr.open();
});
$('#datetimeend .bi-calendar').parent().on('click', function() {
    document.querySelector('#active_end')._flatpickr.open();
});

// Fix number input clamping for Firefox
$('input[type=number]').blur(function() {
    let newnum = 1 * $(this).val();
    const min = 1 * $(this).data('min');
    const max = 1 * $(this).data('max');

    if (isNaN(newnum)) newnum = 0;

    if (newnum < min) newnum = min;
    else if (newnum > max) newnum = max;

    $(this).val(newnum);
});
