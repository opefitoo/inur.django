window.addEventListener("load", function() {
    (function($) {
        $('#toggle-week').click(function () {
            $('#toggle-month').toggle();
        });
    })(django.jQuery);
});