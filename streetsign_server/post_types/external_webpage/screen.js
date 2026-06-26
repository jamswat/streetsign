{
    render(zone, data) {
        'use strict';
        let newhtml;
        let $iframe;

        console.log('embedding new external webpage');

        $iframe = $('<iframe scrolling="no" frameborder="no">...</iframe>')
            .attr('width', $(zone).width())
            .attr('height', $(zone).height())
            .attr('src', data.content.url);

        if (data.zone && data.zone.type === 'scroll') {
            newhtml = $(`<div class="post post_html post_scrolling"><div class="post_inner post_reset_fontsize"></div></div>`).prependTo(zone);
        } else {
            newhtml = $(`<div class="post post_html"><div class="post_inner post_reset_fontsize"></div></div>`)
                .prependTo(zone);
        }

        newhtml.find('.post_inner').append($iframe);

        return newhtml;
    }
}
