$(function() {
    // Remove jet select2 if autocomplete-light is used
    var autocomplete_light_selects = $('select[data-is_custom_autocomplete_light="true"]');
    if (0 < autocomplete_light_selects.length) {
        $.each(autocomplete_light_selects, function(index, item) {
            var parent = $(item).parent();
            parent.find('.select2-container--jet').remove();
            var autocomplete_light = parent.find('.select2-container--default');
            autocomplete_light.removeClass('select2-container--default').addClass('select2-container--jet');

            $(item).on("select2:open", function() {
                $('.select2-container--default').removeClass('select2-container--default').addClass('select2-container--jet');
            });

            $.each($(item).data('forward'), function(index, name){
                $('[name$="'+name+'"]').on('change', function() {
                    $(item).val(null).trigger('change');
                });
            });
        });
    }
});