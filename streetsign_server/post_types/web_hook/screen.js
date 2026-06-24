{
    render(zone, data) {
        $.post(data.content.render_url);
        return $(`<div class="post post_webhook">...</div>`).prependTo(zone);
    },
    display(data) {
        const url = (data.content.display_url.match(/.*:\/\/.*/) !== null ? 'http://' : '') + data.content.display_url;
        console.log(`Trying to start local stream-player: ${url}`);
        $('#zones').fadeOut();
        $.post(url);
    },
    hide(data) {
        const url = (data.content.display_url.match(/.*:\/\/.*/) !== null ? 'http://' : '') + data.content.hide_url;
        console.log(`Trying to stop local stream-player: ${url}`);
        $('#zones').fadeIn();
        $.post(url);
    }
}
