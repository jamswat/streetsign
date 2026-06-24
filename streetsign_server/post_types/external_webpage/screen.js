{
    render(zone, data) {
        'use strict';
        let newhtml;

        console.log('embedding new external webpage');

        newhtml = `<iframe scrolling="no" width="${$(zone).width()}" height="${$(zone).height()}" frameborder="no" src="${data.content.url}">...</iframe>`;

        if (data.zone && data.zone.type === 'scroll') {
            newhtml = $(`<div class="post post_html post_scrolling"><div class="post_inner post_reset_fontsize">`
                        + newhtml
                        + `</div></div>`).prependTo(zone);
        } else {
            newhtml = $(`<div class="post post_html"><div class="post_inner post_reset_fontsize">`
                    + newhtml
                    + `</div></div>`)
                    .prependTo(zone);
        }

        return newhtml;
    }
}
