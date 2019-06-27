jQuery(function() {
    jQuery('.inline-group').on('click', '.copy_inline', function(e) {
        e.preventDefault();
        var inline_group = jQuery(this).closest('.inline-group');
        var add_link = inline_group.find('.add-row a');
        if (!add_link.is(':visible')) {
            return false;
        }

        add_link.trigger('click');
        var new_row = inline_group.find('.form-row:not(.empty-form):last');
        var source_row = jQuery(this).closest('.form-row');

        var row_id_suffix = '-id';
        var new_row_inputs = new_row.find('input,select');
        jQuery.each(source_row.find('input,select'), function(index, source_input) {
            var new_row_input = new_row_inputs[index];
            if ('undefined' == typeof (new_row_input)) {
                return;
            }

            var input_id = jQuery(new_row_input).attr('id');
            if ('undefined' == typeof (input_id)) {
                input_id = '';
            }
            if (input_id.indexOf(row_id_suffix, input_id.length - row_id_suffix.length) === -1) {
                if ('select' == jQuery(new_row_input)[0].nodeName.toLowerCase()) {
                    jQuery(new_row_input).html(jQuery(source_input).html());
                }
                jQuery(new_row_input).val(jQuery(source_input).val());
                jQuery(new_row_input).trigger('change');
            }
        });
    });
});