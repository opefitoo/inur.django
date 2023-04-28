from django.utils import timezone

from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail


def get_door_events(event_day=None):
    sheet_year = timezone.now().year
    sheet_month = timezone.now().month

    sheets = SimplifiedTimesheet.objects.filter(time_sheet_year=sheet_year, time_sheet_month=sheet_month)
    for sheet in sheets:
        # details = sheet.simplifiedtimesheetdetail_set()
        details = SimplifiedTimesheetDetail.objects.filter(simplified_timesheet_id=sheet.id,
                                                           start_date__day=event_day.day if event_day else timezone.now().day)
        for detail in details:
            print(detail)

    return sheets


