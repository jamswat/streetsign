{
    render: function(zone, data) {
        'use strict';

        console.log('rendering video post');

        var audioEnabled = data.content.audio_enabled,
            $video = $('<video loop playsinline>')
                .attr('width', $(zone).width())
                .attr('height', $(zone).height())
                .attr('src', data.content.file_url)
                .css({ objectFit: 'contain' }),
            $wrapper;

        if (audioEnabled) {
            var $overlay = $('<div>Tap to start audio</div>')
                .css({
                    position: 'absolute', top: 0, left: 0,
                    width: '100%', height: '100%',
                    background: 'rgba(0,0,0,0.4)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    zIndex: 10,
                    fontSize: '1.2em',
                    fontWeight: 'bold'
                });

            $overlay.on('click', function() {
                $video[0].play();
                $overlay.remove();
            });

            if (('type' in data.zone) && (data.zone.type == 'scroll')) {
                $wrapper = $('<div class="post post_html post_scrolling">'
                    + '<div class="post_inner post_reset_fontsize"></div></div>')
                    .prependTo(zone);
            } else {
                $wrapper = $('<div class="post post_html">'
                    + '<div class="post_inner post_reset_fontsize"></div></div>')
                    .prependTo(zone);
            }

            $wrapper.find('.post_inner').css('position', 'relative')
                .append($video).append($overlay);
        } else {
            $video.attr('autoplay', true).attr('muted', true);

            if (('type' in data.zone) && (data.zone.type == 'scroll')) {
                $wrapper = $('<div class="post post_html post_scrolling">'
                    + '<div class="post_inner post_reset_fontsize"></div></div>')
                    .prependTo(zone);
            } else {
                $wrapper = $('<div class="post post_html">'
                    + '<div class="post_inner post_reset_fontsize"></div></div>')
                    .prependTo(zone);
            }

            $wrapper.find('.post_inner').append($video);
        }

        return $wrapper;
    }
}
