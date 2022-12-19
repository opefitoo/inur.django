let $ = django.jQuery;
$(function () {
    function maskCodeSn() {
        if (!$('input[name="is_private"]').prop('checked')) {
            $('input[name="code_sn"]').mask('9999 99 99 999 99', {placeholder: 'NNNN NN NN NNN NN'});
        }
    }

    $('#patient_form').on('change', 'input[name="is_private"]', function (e) {
        if ($(this).prop('checked')) {
            $('input[name="code_sn"]').unmask();
        } else {
            maskCodeSn();
        }
    });

    maskCodeSn();
});
