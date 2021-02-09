function biss(arg) {
  var start = 11;
  var totalHours = 0;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getActiveSheet();
  var sumHoursPerRow = 0
  for(var j=11; j < 24; j++) {
    var startStr = "E"+j+":AI"+j;
    var range = SpreadsheetApp.getActiveSpreadsheet().getRange(startStr);
    if(range.getNumColumns() > 0) {
      var sum = 0;
      for(var i=1; i < range.getNumColumns(); i++) {
        if(arg == range.getCell(1,i).getValue()) {
          sum = sum +1;
        }
      }
    }
    var diff = sheet.getRange(j, 4).getValue() - sheet.getRange(j, 3).getValue();
    sumHoursPerRow += diff * sum;
  }
  return sumHoursPerRow / (3600000);
}

function totalH(range, arg) {
  var totalHr = 0;
  var totalPassages = 0;
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  for(var ligne=0; ligne < range.length; ligne++){
    var nombrePassages = 0;
    for(var colonne=0; colonne < range[ligne].length; colonne++) {
      if(arg == range[ligne][colonne]) {
        nombrePassages = nombrePassages +1;
        totalPassages = totalPassages + 1;
      }
    }
    totalHr += (sheet.getRange(ligne+11, 4).getValue() - sheet.getRange(ligne+11, 3).getValue()) * nombrePassages;
  }
  return "hr:" + totalHr / (3600000) + "-p: " + totalPassages;
}

function whoIsFree(range) {
flattenedRange = [];
  for(var ligne=0; ligne < range.length; ligne++){
    flattenedRange.push(range[ligne][0]);
  }
  var arr = [];
    if(!flattenedRange.includes("NA")) {
        arr.push("NA");
      }
   if(!flattenedRange.includes("SR")){
      arr.push("SR");
    }
  if(!flattenedRange.includes("AD")){
      arr.push("AD");
    }
   if(!flattenedRange.includes("VM")){
      arr.push("VM");
   }
  if(!flattenedRange.includes("CC")){
      arr.push("CC");
   }
  return arr;
}


