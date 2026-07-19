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
    Screen Client Aliases Editor - Alpine.js data factory

*************************************************************/
'use strict';

window.makeAliasesEditor = function(initialList, screenNames, screenTypes) {
    // Snapshot original names before we inject any missing ones.
    var knownNames = screenNames.slice();

    // Add any alias screen_names missing from the dropdown list so the
    // <select> always has a matching <option> at init time — Alpine's
    // x-model falls back to the first option when no option matches.
    (initialList || []).forEach(function(a) {
        var name = a.screen_name || '';
        if (name && !screenNames.includes(name)) {
            screenNames.push(name);
        }
    });

    var aliases = (initialList || []).map(function(a) {
        var resolvedScreen = a.screen_name || screenNames[0] || 'Default';
        return {
            name: a.name || 'client-name',
            show_on_dashboard: a.show_on_dashboard || false,
            screen_name: resolvedScreen,
            screen_type: a.screen_type || 'basic',
            fadetime: a.fadetime != null ? a.fadetime : null,
            scrollspeed: a.scrollspeed != null ? a.scrollspeed : null,
            forceaspect: a.forceaspect != null ? a.forceaspect : null,
            forcetop: a.forcetop != null ? a.forcetop : null
        };
    });

    return {
        aliases: aliases,
        screenNames: screenNames,
        screenTypes: screenTypes,

        screenExists: function(alias) {
            return knownNames.includes(alias.screen_name);
        },

        urlFor: function(alias) {
            return '/client/' + alias.name;
        },

        addAlias: function() {
            var firstScreen = knownNames.length ? knownNames[0] : 'Default';
            this.aliases.push({
                name: 'client-name',
                show_on_dashboard: false,
                screen_name: firstScreen,
                screen_type: 'basic',
                fadetime: null,
                scrollspeed: null,
                forceaspect: null,
                forcetop: null
            });
        },

        deleteAlias(idx) {
            confirmAction('Really delete this alias?', () => {
                this.aliases.splice(idx, 1);
            });
        },

        sanitizeAliasName(alias) {
            alias.name = alias.name.replace(/[^a-zA-Z0-9 _-]/g, '').replace(/\s+/g, '-');
        },

        saveAliases() {
            $.post('/aliases',
                { 'aliases': JSON.stringify(this.aliases) },
                function() { showToast('Aliases saved.', 'success'); })
             .fail(function(jqXHR) {
                var msg = jqXHR.responseJSON?.error || 'Failed to save aliases.';
                showToast(msg, 'error');
             });
        }
    };
};
