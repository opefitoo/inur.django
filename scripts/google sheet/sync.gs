function createEventCalendar() {

  cleanupEvents(2021, 2);

  var sync_result = SpreadsheetApp.getActive().getSheetByName("sync result");

  var timezone = SpreadsheetApp.getActive().getSpreadsheetTimeZone();

  var event = "";
  var range = SpreadsheetApp.getActiveSheet().getRange("E10:AI34");
  var lastColumn = range.getLastColumn();
  var lastRow = range.getLastRow();
  var clientRangeValues = SpreadsheetApp.getActiveSheet().getRange("B10:D34").getValues();
  var dayValues = SpreadsheetApp.getActiveSheet().getRange("E8:AI8").getValues();
  var rangeValues = range.getValues();
  var colonnes = rangeValues[0].length;
  var lignes = rangeValues.length;
  var mysheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  for (i = 0; i < colonnes; i++) {
    for (j = 0; j < lignes; j++) {

      var current_employee = rangeValues[j][i];

      if (["SR", "VM", "NA", "CC", "AA"].includes(current_employee)) {
        Logger.log("I:" + i + ",J:" + j);
        if (i == 10 && j == 22) {
          Logger.log(clientRangeValues[j][1])
        }
        var client = clientRangeValues[j][0].split(",")[1];
        var day = Utilities.formatDate(new Date(dayValues[0][i]), timezone, 'YYYY-MM-dd')
        Logger.log("I:" + i + ",J:" + j + " client:" + client + ",on " + day)

        var from_time = Utilities.formatDate(new Date(clientRangeValues[j][1]), timezone, 'HH:mm');
        var to_time = Utilities.formatDate(new Date(clientRangeValues[j][2]), timezone, 'HH:mm');

        var result = "";

        result = callInur(day, from_time, to_time, client, current_employee)
        sync_result.appendRow([current_employee, result.getResponseCode(), result.toString()]);
      }
    };
  };
  //Logger.log(event);
}

function cleanupEvents(year, month) {

  var token = "get_one";

  var data = {    
    "year": year,
    "month": month,
  }

  var options = {
    'method': 'GET'    
    , 'headers': {      
      
      'Authorization': 'Token ' + token
    }    
    , muteHttpExceptions: true
    , payload: data
  };

  // Call Inur API
  var response = UrlFetchApp.fetch(
    "https://inur-sur.herokuapp.com/api/v1/cleanup_event/",
    options);
  Logger.log("Deleted: " + response.getContentText());

  return response;

}


function callInur(day, time_start, time_end, patient_id, employee_abr) {

  var token = "get_one";

  var data = {
    "day": day,
    "time_start_event": time_start,
    "time_end_event": time_end,
    "state": 2,
    "event_type": 2,
    "patient": patient_id,
    "employees": employee_abr,
    "created_by": 'planning script'
  }
  var payload = JSON.stringify(data);

  var options = {
    'method': 'POST'
    , 'headers': {
      "Accept": "application/json",
      "Content-Type": "application/json",
      'Authorization': 'Token ' + token
    }
    , payload: payload
    , muteHttpExceptions: true
  };

  // Call Inur API
  var response = UrlFetchApp.fetch("https://inur-sur.herokuapp.com/api/v1/event_list/", options);
  Logger.log(response.getContentText());

  return response;

}


function getActiveSheetId() {
  var id = SpreadsheetApp.getActive().getSheetByName("sync result");
  Logger.log(id.toString());
  return id;
}