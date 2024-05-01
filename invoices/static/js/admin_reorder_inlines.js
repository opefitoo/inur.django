window.onload = function () {
  // Delay execution of your script by 500 milliseconds
  setTimeout(function () {
    //console.log("Custom script loaded for admin inline forms.");

    django.jQuery('.tabular.inline-related.last-related').each(function () {
      // find table element
      var $inlineTable = django.jQuery(this);
      var $tbody = $inlineTable.find('tbody');
      // find last row
      var $lastRow = $tbody.find('tr').last();
      //console.log('lastRow:', $lastRow);
      // move last row to the top
      $lastRow.detach().prependTo($tbody);
    });
  }, 500);  // Adjust the delay as needed
};

// if add new button is clicked then move the last row to the top
document.addEventListener("DOMContentLoaded", function () {
    django.jQuery(document).on('formset:added', function(event, $row, formsetName, addRowButton) {
      // now find the target element
      var $newlyCreatedRow = django.jQuery(event.target);
      // now find the parent element of the $newlyCreatedRow
      var $tbody = $newlyCreatedRow.parent();
      // move it right after the first add-row button
      $newlyCreatedRow.detach().insertAfter($tbody.find('.add-row'));
    });
});
