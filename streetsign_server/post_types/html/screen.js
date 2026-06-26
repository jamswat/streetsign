{
    render(zone, data) {
        'use strict';
        let newhtml;

        console.log('making new html');

        if (data.zone && data.zone.type === 'scroll') {
            newhtml = $(`<div class="post post_html post_scrolling"><div class="post_inner ql-editor">`
                           + magic_vars(data.content.content).replace('<br/>', ' ')
                           + `</div></div>`).prependTo(zone);
        } else {
            newhtml = $(`<div class="post post_html"><div class="post_inner ql-editor">`
                    + magic_vars(data.content.content)
                    + `</div></div>`)
                    .prependTo(zone);
        }

        // Populate any magic_time/magic_date placeholders immediately so they
        // are visible right away (in fade zones nothing else fills them) and
        // so the font auto-fit / scroll-width measurements use the real text.
        fill_magic_vars(newhtml);

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
