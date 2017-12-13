$(function() {
    function pad(num) {
        var size = 2;
        var s = num+"";
        while (s.length < size) s = "0" + s;

        return s;
    }

    function convert_to_24h(time_str) {
        var time = time_str.match(/(\d+):(\d+) (\w)/);
        var hours = Number(0);
        var minutes = Number(0);
        var meridian = 'a';
        if (null !== time) {
            hours = Number(time[1]);
            minutes = Number(time[2]);
            meridian = time[3].toLowerCase();
        }
        else {
            time = time_str.match(/(\d+) (\w)/);
            hours = Number(time[1]);
            minutes = Number(0);
            meridian = time[2].toLowerCase();
        }

        if (meridian == 'p' && hours < 12) {
            hours += 12;
        }
        else if (meridian == 'a' && hours == 12) {
            hours -= 12;
        }

        return [pad(hours), pad(minutes)];
    }

    $('fieldset').on('click', '.default_time', function(e) {
        e.preventDefault();
        var time_parts = convert_to_24h($(this).val());
        var time_value = time_parts.join(':');

        $(this).closest('.datetime').find('.vTimeField').val(time_value);
    });
});
