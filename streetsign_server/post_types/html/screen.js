{
    render(zone, data) {
        'use strict';
        let newhtml;

        console.log('making new html');

        if (data.zone && data.zone.type === 'scroll') {
            newhtml = $(`<div class="post post_html post_scrolling"><div class="post_inner">`
                           + magic_vars(data.content.content).replace('<br/>', ' ')
                           + `</div></div>`).prependTo(zone);
        } else {
            newhtml = $(`<div class="post post_html"><div class="post_inner">`
                    + magic_vars(data.content.content)
                    + `</div></div>`)
                    .prependTo(zone);
        }

        if (data.fontsize > 0) {
            newhtml.children('.post_inner').css('font-size', data.fontsize + 'pt');
        } else {
            reduce_font_size_to_fit(newhtml.children('.post_inner'), $(zone));
        }

        if (data.content.owntextcolor) {
            try { newhtml.css('color', data.content.color); } catch (e) {}
        }

        return newhtml;
    }
}
