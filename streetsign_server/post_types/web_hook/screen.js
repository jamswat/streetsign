{
    render(zone, data) {
        $.post(data.content.render_url);
        return $(`<div class="post post_webhook">...</div>`).prependTo(zone);
    },
    display(data) {
        const target = data.content.display_url;
        const url = (target.match(/.*:\/\/.*/) !== null ? '' : 'http://') + target;
        console.log(`Trying to start local stream-player: ${url}`);
        $('#zones').fadeOut();
        $.post(url);
    },
    hide(data) {
        const target = data.content.hide_url;
        const url = (target.match(/.*:\/\/.*/) !== null ? '' : 'http://') + target;
        console.log(`Trying to stop local stream-player: ${url}`);
        $('#zones').fadeIn();
        $.post(url);
    }
}
