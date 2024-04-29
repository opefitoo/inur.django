document.addEventListener("DOMContentLoaded", function() {
    function moveNewFormsToTop() {
        console.log('Attempting to move new forms to the top in TabularInline...');

        // Target the inline table specifically
        django.jQuery('.tabular.inline-related.last-related').each(function() {
          console.log('Found a TabularInline.');
            var $inlineTable = django.jQuery(this);

            // Find all rows and check if they are new
            $inlineTable.find('tr.form-row').each(function() {
                var isNew = !django.jQuery(this).find('input[id$="-id"]').val();
                if (isNew) {
                    console.log('Moving a new tabular form row to the top.');
                    // Move this new row to right after the header row in the table
                    django.jQuery(this).insertAfter($inlineTable.find('tr:first'));
                }
            });
        });
    }

    // Initial call
    moveNewFormsToTop();

    // Bind to the 'Add another' link to handle dynamic form addition
    django.jQuery('.add-row a').click(function() {
        console.log('Add another clicked in TabularInline.');
        setTimeout(moveNewFormsToTop, 100);  // Delay to allow form to be added
    });
});
