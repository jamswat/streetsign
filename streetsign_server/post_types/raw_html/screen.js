{
    render: function(zone, data) {
        'use strict';

        console.log('embedding new raw html');

        var $iframe = $('<iframe scrolling="no" frameborder="no">...</iframe>')
            .attr('width', $(zone).width())
            .attr('height', $(zone).height())
            .attr('srcdoc', data.content.content);

        var $wrapper;

        if (('type' in data.zone) && (data.zone.type == 'scroll')) {
            $wrapper = $('<div class="post post_html post_scrolling"><div class="post_inner post_reset_fontsize"></div></div>')
                .prependTo(zone);
        } else {
            $wrapper = $('<div class="post post_html"><div class="post_inner post_reset_fontsize"></div></div>')
                .prependTo(zone);
        }

        $wrapper.find('.post_inner').append($iframe);

        return $wrapper;
    }
}
