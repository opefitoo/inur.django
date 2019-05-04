jQuery(function() {
    jQuery('#prestations-empty .field-delete').html('');

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)jQuery/.test(method));
    }

    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    jQuery('.inline-group').on('click', '.deletelink', function(e) {
        e.preventDefault();
        var jQueryinline_group = jQuery(this).closest('.inline-group');
        var prefix = jQueryinline_group.data('inline-formset').options.prefix;

        var form_row = jQuery(this).closest('.form-row');
        var prestation_id = jQuery(this).data('prestation_id');

        var is_confirmed = confirm("Do you want to delete Prestation?");
        if (true == is_confirmed) {
            var csrftoken = getCookie('csrftoken');
            jQuery.ajax({
                url: jQuery(this).attr('href'),
                method: 'POST',
                data: {
                    'prestation_id': prestation_id
                },
                beforeSend: function(xhr, settings) {
                    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    }
                },
                success: function(response) {
                    form_row.remove();
                    var jQuerytotalFormsInput = jQueryinline_group.find('[name="' + prefix + '-TOTAL_FORMS"]');
                    console.log(jQuerytotalFormsInput, jQueryinline_group, prefix);
                    var totalForms = parseInt(jQueryinline_group.find('.inline-related').length);
                    jQuerytotalFormsInput.val(totalForms);
                }
            });
        }
    });
});