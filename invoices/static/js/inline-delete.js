$(function() {
    $('#prestations-empty .field-delete').html('');

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
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

    $('.inline-group').on('click', '.delete_inline', function(e) {
        e.preventDefault();
        var $inline_group = $(this).closest('.inline-group');
        var prefix = $inline_group.data('inline-formset').options.prefix;

        var form_row = $(this).closest('.form-row');
        var prestation_id = $(this).data('prestation_id');

        var is_confirmed = confirm("Do you want to delete Prestation?");
        if (true == is_confirmed) {
            var csrftoken = getCookie('csrftoken');
            $.ajax({
                url: $(this).attr('href'),
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
                    var $totalFormsInput = $inline_group.find('[name="' + prefix + '-TOTAL_FORMS"]');
                    console.log($totalFormsInput, $inline_group, prefix);
                    var totalForms = parseInt($inline_group.find('.inline-related').length);
                    $totalFormsInput.val(totalForms);
                }
            });
        }
    });
});