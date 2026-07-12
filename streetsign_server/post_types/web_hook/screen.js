{
    render(zone, data) {
        $.post(data.content.render_url);
        return $(`<div class="post post_webhook">...</div>`).prependTo(zone);
    },
    display(data) {
        const target = data.content.display_url;
        const url = (target.match(/.*:\/\/.*/) !== null ? '' : 'http://') + target;
        console.log(`Trying to start local stream-player: ${url}`);
        $('#zones').css('transition', 'opacity 0.5s').css('opacity', 0);
        $.post(url);
    },
    hide(data) {
        const target = data.content.hide_url;
        const url = (target.match(/.*:\/\/.*/) !== null ? '' : 'http://') + target;
        console.log(`Trying to stop local stream-player: ${url}`);
        $('#zones').css('transition', 'opacity 0.5s').css('opacity', 1);
        $.post(url);
    }
}
