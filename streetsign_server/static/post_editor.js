$('.post_type_button').click(function(e) {
    const postType = $(this).data('posttype');
    $('input[name="post_type"]').val(postType);

    const container = $('#postcontentblock-type');
    container.html('<div class="skeleton skeleton-text" style="width:80%"></div><div class="skeleton skeleton-text"></div><div class="skeleton skeleton-text-sm"></div><div class="skeleton skeleton-text" style="width:40%"></div>');
    container.load(
        window.POST_TYPE_URL(postType)
    );

    $(this).parent('li').addClass('active').siblings().removeClass('active');
    $(this).addClass('active').closest('.nav-tabs').find('.nav-link').not(this).removeClass('active');
});

// Auto-select first post type on page load so content area is populated immediately
$('.post_type_button').first().click();
