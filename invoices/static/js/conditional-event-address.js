jQuery(document).ready(function() {
    django.jQuery('input[name="at_office"]').change(function () {
        if (django.jQuery(this).is(':checked')) {
            django.jQuery('#id_event_address').prop('disabled', true);
//             django.jQuery.ajax({
//    type: "GET",
//    dataType: "jsonp",
//    url: "http://127.0.0.1:8000/api/v1/setting",
//    success: function(data){
//      alert(data);
//    }
// });
        } else if (django.jQuery(this).not(':checked')) {
            django.jQuery('#id_event_address').prop('disabled', false);
        }
    });
});

