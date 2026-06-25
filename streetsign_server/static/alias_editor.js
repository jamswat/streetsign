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
    const aliases = (initialList || []).map(function(a) {
        return {
            name: a.name || 'client-name...',
            show_on_dashboard: a.show_on_dashboard || false,
            screen_name: a.screen_name || 'Default',
            screen_type: a.screen_type || 'basic',
            fadetime: a.fadetime || null,
            scrollspeed: a.scrollspeed || null,
            forceaspect: a.forceaspect || null,
            forcetop: a.forcetop || null
        };
    });

    return {
        aliases: aliases,
        screenNames: screenNames,
        screenTypes: screenTypes,

        urlFor(alias) {
            return '/client/' + alias.name;
        },

        addAlias() {
            this.aliases.push({
                name: 'client-name...',
                show_on_dashboard: false,
                screen_name: 'Default',
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

        saveAliases() {
            $.post('/aliases',
                { 'aliases': JSON.stringify(this.aliases) },
                function() { showToast('Aliases saved.', 'success'); })
             .fail(function() { showToast('Failed to save aliases.', 'error'); });
        }
    };
};
