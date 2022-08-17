from abc import ABC
from datetime import datetime

import holidays
from django.utils import timezone


class TotalTimesheetCalculations(ABC):
    def __init__(self, total_hours, total_sundays, total_hours_during_public_holidays,
                 total_hours_holidays_absence_taken):
        self.list_of_public_holidays_worked = None
        self.list_of_sundays_worked = None
        self.total_hours = total_hours
        self.total_sundays = total_sundays
        self.total_hours_during_public_holidays = total_hours_during_public_holidays
        self.total_hours_holidays_absence_taken = total_hours_holidays_absence_taken

    def add_sunday_date_worked(self, sunday):
        if self.list_of_sundays_worked is None:
            self.list_of_sundays_worked = []
        self.list_of_sundays_worked.append(sunday)

    def add_public_holidays_date_worked(self, public_holiday):
        if self.list_of_public_holidays_worked is None:
            self.list_of_public_holidays_worked = []
        self.list_of_public_holidays_worked.append(public_holiday)


def display_in_hours_minutes_value(total_seconds):
    return "%d h:%d mn" % (total_seconds // 3600, (total_seconds % 3600) // 60)


def calculate_total_hours(simplified_timesheet_object):
    format_data = "%d/%m/%Y"

    lu_holidays = holidays.Luxembourg()
    total = timezone.timedelta(0)
    total_sundays = timezone.timedelta(0)
    total_public_holidays = timezone.timedelta(0)
    sundays = []
    public_holidays = []
    for v in simplified_timesheet_object.simplifiedtimesheetdetail_set.all():
        delta = datetime.combine(v.start_date, v.end_date) - \
                datetime.combine(v.start_date, v.start_date.time())
        total = total + delta
        if v.start_date.astimezone().weekday() == 6:
            total_sundays = total_sundays + delta
            sundays.append(datetime.strftime(v.start_date, format_data))
        if v.start_date in lu_holidays:
            total_public_holidays = total_public_holidays + delta
            public_holidays.append(datetime.strftime(v.start_date, format_data))
    # calculated_hours["total_hours_holidays_taken"] = self.absence_hours_taken()
    calculations_object = TotalTimesheetCalculations(total_hours=total,
                                                     total_sundays=total_sundays,
                                                     total_hours_during_public_holidays=total_public_holidays,
                                                     total_hours_holidays_absence_taken=0)
    calculations_object.list_of_sundays_worked = sundays
    calculations_object.list_of_public_holidays_worked = public_holidays

    return calculations_object
