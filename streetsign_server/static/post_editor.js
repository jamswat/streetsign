$('.post_type_button').click(function(e) {
    $('#postcontentblock-type').load(
        window.POST_TYPE_URL($(this).data('posttype'))
    );

    $(this).parent('li').addClass('active').siblings().removeClass('active');
    $(this).addClass('active').closest('.nav-tabs').find('.nav-link').not(this).removeClass('active');
    $('#title-input').show();
});

$('#title-input').hide();
