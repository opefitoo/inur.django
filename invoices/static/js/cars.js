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
    await fetchCarLocationsAndStatus(id);
    //fetchLockStatus(id);
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
        row += '<td>' + val.name + '</td>';
        row += '<td id="car-lock-status-' + val.id + '">Loading...</td>';
        row += '<td id="car-location-' + val.id + '">Loading...</td>';
        row += '<td><button class="lock" data-id="' + val.id + '">Lock</button></td>';
        row += '<td><button class="unlock" data-id="' + val.id + '">Unlock</button></td>';
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
      }
    });
  });
});
