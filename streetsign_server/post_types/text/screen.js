{
    render(zone, data) {
        const newhtml = $(`<div class="post post_text"><div class="post_inner">`
                + magic_vars(data.content.content)
                + `</div></div>`)
                .prependTo(zone);

        console.log('making new text-post');

        // Populate any magic_time/magic_date placeholders immediately so they
        // are visible right away and measured correctly during font auto-fit.
        fill_magic_vars(newhtml);

        if (data.fontsize > 0) {
            newhtml.children('.post_inner').css('font-size', data.fontsize + 'pt');
        } else {
            reduce_font_size_to_fit(newhtml.children('.post_inner'), $(zone));
        }

        return newhtml;
    }
}
