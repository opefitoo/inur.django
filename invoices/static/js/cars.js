function generateGoogleMapsUrl(locationData) {
  if (locationData === undefined)
    return 'No location available';
  console.log('Location:', locationData);
  const latitude = locationData.location.location.latitude;
  const longitude = locationData.location.location.longitude;
  return `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;
}

function getCookie(name) {
  const value = "; " + document.cookie;
  const parts = value.split("; " + name + "=");
  if (parts.length == 2) return parts.pop().split(";").shift();
}

function fetchCarLocationsAndStatus(carId) {
  var csrftoken = getCookie('csrftoken');
  var cookietoken = getCookie('auth_token');

  $.ajax({
    url: '/api/v1/car_location/' + carId + '/',
    type: 'GET',
    beforeSend: function (xhr) {
      xhr.setRequestHeader('X-CSRFToken', csrftoken);
      xhr.setRequestHeader('Authorization', 'Token ' + cookietoken);
    },
    success: function (data) {

      $('#car-location-' + carId).html('<a href="' + generateGoogleMapsUrl(data) + '">Google Maps Link</a>');
    },
    error: function (xhr, textStatus, errorThrown) {
      console.error('Error fetching car location:', errorThrown);
    }
  });
}

function fetchLockStatus(carId) {
  var csrftoken = getCookie('csrftoken');
  var cookietoken = getCookie('auth_token');
  $.ajax({
    url: '/api/v1/is_car_locked/' + carId + '/',
    type: 'GET',
    beforeSend: function (xhr) {
      xhr.setRequestHeader('X-CSRFToken', csrftoken);
      xhr.setRequestHeader('Authorization', 'Token ' + cookietoken);
    },
    success: function (lockedData) {
      // format json data to console
      console.log("*** is car locked data :" + JSON.stringify(lockedData, null, 4) + " for carId" + carId + " ***");
      console.log('isLocked:', lockedData.locked.isLocked);
      console.log($('#car-lock-status-' + carId));
      if (lockedData.locked.isLocked == true) {
        $('#car-lock-status-' + carId).text('Locked');
      } else {
        $('#car-lock-status-' + carId).text('-');
      }
    },
    error: function (xhr, textStatus, errorThrown) {
      console.error('Error fetching car lock status:', errorThrown);
    }
  });
}

async function fetchCarDataAndStatus(id) {
  try {
    /*await fetchCarLocationsAndStatus(id);
    fetchLockStatus(id).then((lockedData) => {
      if (lockedData.locked.isLocked == true) {
        $('#car-lock-status-' + id).text('Locked');
      } else {
        $('#car-lock-status-' + id).text('-');
      }
    });*/

    var csrftoken = getCookie('csrftoken');
    var cookietoken = getCookie('auth_token');

    // Call the can_user_lock_car API
    $.ajax({
      url: '/api/v1/can_user_lock_car/' + id + '/',
      type: 'GET',
      beforeSend: function (xhr) {
        xhr.setRequestHeader('X-CSRFToken', csrftoken);
        xhr.setRequestHeader('Authorization', 'Token ' + cookietoken);
      },
      success: function (data) {
        if (data.error || !data.can_lock) {
          $('#car-lock-status-' + id).text('Indispo');
          $('#lock-unlock-button').prop('disabled', false);
        }
      },
      error: function (xhr, textStatus, errorThrown) {
        console.error('Error fetching car lock status:', errorThrown);
      }
    });
  } catch (error) {
    console.error('Error:', error);
  }
}

$(document).ready(function () {
  // Get the CSRF token
  var csrftoken = getCookie('csrftoken');
  var cookietoken = getCookie('auth_token');
  console.log('Cookie token:', cookietoken);

  // Use the predefined token for subsequent requests
  $.ajax({
    url: '/api/v1/cars/',
    type: 'GET',
    beforeSend: function (xhr) {
      console.log('Token:', localStorage.getItem('token'));
      xhr.setRequestHeader('X-CSRFToken', csrftoken);
      xhr.setRequestHeader('Authorization', 'Token ' + cookietoken);
    },
    success: function (data) {
      $.each(data, function (key, val) {
        var row = '<tr>';
        let bookedForName = val.booked_for ? val.booked_for.user.first_name : 'Not booked';

        row += '<td>' + val.name + '</td>';
        row += '<td id="car-lock-status-' + val.id + '">Loading...</td>';
        row += '<td id="car-location-' + val.id + '">Loading...</td>';
        row += '<td id="car-booked-for' + val.id + '">' + bookedForName + '</td>';
        let canLock = val.can_lock;
        let canUnlock = val.can_unlock;
        if (canLock) {
          row += '<td><button class="lock" data-id="' + val.id + '">Lock</button></td>';
        } else {
          row += '<td><button class="lock" data-id="' + val.id + '" disabled>Lock</button></td>';
        }

        if (canUnlock) {
          row += '<td><button class="unlock" data-id="' + val.id + '">Unlock</button></td>';
        } else {
          row += '<td><button class="unlock" data-id="' + val.id + '" disabled>Unlock</button></td>';
        }
        //row += '<td><button class="lock" data-id="' + val.id + '">Lock</button></td>';
        //row += '<td><button class="unlock" data-id="' + val.id + '">Unlock</button></td>';
        row += '</tr>';
        $('#carTable tbody').append(row);

        // Fetch car location and lock status
        fetchCarDataAndStatus(val.id);
      });
    },
    error: function (xhr, textStatus, errorThrown) {
      console.error('Error fetching car data:', errorThrown);
    }
  });

  $(document).on('click', '.lock', function () {
    var carId = $(this).data('id');
    $.ajax({
      url: '/api/v1/lock_car/' + carId + '/',
      type: 'POST',
      beforeSend: function (xhr) {
        xhr.setRequestHeader('X-CSRFToken', csrftoken);
        xhr.setRequestHeader('Authorization', 'Token ' + cookietoken);
      },
      success: function () {
        alert('Car locked successfully');
      },
      error: function (jqXHR, textStatus, errorThrown) {
        // Handle error here
        console.error("Error locking car: ", textStatus, ", Details: ", errorThrown);
        console.error("Response: ", jqXHR.responseText);
        alert("An error occurred while locking the car: " + jqXHR.responseText);
      }
    });
  });

  $(document).on('click', '.unlock', function () {
    var carId = $(this).data('id');
    $.ajax({
      url: '/api/v1/unlock_car/' + carId + '/',
      type: 'POST',
      beforeSend: function (xhr) {
        xhr.setRequestHeader('X-CSRFToken', csrftoken);
        xhr.setRequestHeader('Authorization', 'Token ' + cookietoken);
      },
      success: function () {
        alert('Car unlocked successfully');
      },
      error: function (jqXHR, textStatus, errorThrown) {
        // Handle error here
        console.error("Error unlocking car: ", textStatus, ", Details: ", errorThrown);
        console.error("Response: ", jqXHR.responseText);
        alert("An error occurred while unlocking the car: " + jqXHR.responseText);
      }
    });
  });
});
