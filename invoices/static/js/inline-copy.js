django.jQuery(function () {
    django.jQuery('.inline-group').on('click', '.copy_inline', function (e) {
        e.preventDefault();
        var inline_group = django.jQuery(this).closest('.inline-group');
        var add_link = inline_group.find('.add-row a');
        if (!add_link.is(':visible')) {
            return false;
        }

        add_link.trigger('click');
        var new_row = inline_group.find('.form-row:not(.empty-form):last');
        var source_row = django.jQuery(this).closest('.form-row');

        var new_row_inputs = new_row.find('input,select');
        django.jQuery.each(source_row.find('input,select'), function (index, source_input) {
            var new_row_input = new_row_inputs[index];
            if (typeof (new_row_input) === 'undefined') {
                return;
            }

            var input_id = django.jQuery(new_row_input).attr('id');
            if (typeof (input_id) === 'undefined') {
                input_id = '';
            }

            // Handle date field
            if (input_id.includes('-date') && !input_id.includes('-date_1')) {
                var dateString = django.jQuery(source_input).val();
                var parts = dateString.split('/');
                var day = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10) - 1; // Month is 0-indexed in JS
                var year = parseInt(parts[2], 10);
                var date = new Date(year, month, day);
                date.setDate(date.getDate() + 1); // Increment the date by 1 day

                var newDateValue = ("0" + date.getDate()).slice(-2) + '/' +
                                   ("0" + (date.getMonth() + 1)).slice(-2) + '/' +
                                   date.getFullYear();
                django.jQuery(new_row_input).val(newDateValue);
            } else if (input_id.includes('-date_1')) {
                // Handle time field, copying as-is
                django.jQuery(new_row_input).val(django.jQuery(source_input).val());
            } else {
                django.jQuery(new_row_input).val(django.jQuery(source_input).val());
            }

            django.jQuery(new_row_input).trigger('change');
        });
    });
});
