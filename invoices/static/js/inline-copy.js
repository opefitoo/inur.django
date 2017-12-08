$(function() {
    $('.inline-group').on('click', '.copy_inline', function(e) {
        e.preventDefault();
        var inline_group = $(this).closest('.inline-group');
        inline_group.find('.add-row a').trigger('click');
        var new_row = inline_group.find('.form-row:not(.empty-form):last');
        var source_row = $(this).closest('.form-row');

        var row_id_suffix = '-id';
        var new_row_inputs = new_row.find('input,select');
        $.each(source_row.find('input,select'), function(index, source_input) {
            var new_row_input = new_row_inputs[index];
            if ('undefined' == typeof (new_row_input)) {
                return;
            }

            var input_id = $(new_row_input).attr('id');
            if ('undefined' == typeof (input_id)) {
                input_id = '';
            }
            if (input_id.indexOf(row_id_suffix, input_id.length - row_id_suffix.length) === -1) {
                if ('select' == $(new_row_input)[0].nodeName.toLowerCase()) {
                    $(new_row_input).html($(source_input).html());
                }
                $(new_row_input).val($(source_input).val());
                $(new_row_input).trigger('change');
            }
        });
    });
});