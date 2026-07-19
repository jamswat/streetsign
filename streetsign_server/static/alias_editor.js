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
    // Inject alias screen_names that reference deleted screens into the
    // dropdown list so Alpine's x-model always finds a matching <option>.
    (initialList || []).forEach(function(a) {
        var name = a.screen_name;
        if (a._screen_missing && name && !screenNames.includes(name)) {
            screenNames.push(name);
        }
    });

    var aliases = (initialList || []).map(function(a) {
        return {
            name: a.name || 'client-name',
            show_on_dashboard: a.show_on_dashboard || false,
            screen_name: a.screen_name || screenNames[0] || 'Default',
            screen_type: a.screen_type || 'basic',
            _screen_missing: a._screen_missing || false,
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
            return !alias._screen_missing;
        },

        urlFor: function(alias) {
            return '/client/' + alias.name;
        },

        addAlias: function() {
            var firstScreen = screenNames.length ? screenNames[0] : 'Default';
            this.aliases.push({
                name: 'client-name',
                show_on_dashboard: false,
                screen_name: firstScreen,
                screen_type: 'basic',
                _screen_missing: false,
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
