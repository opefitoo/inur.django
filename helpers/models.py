from abc import ABC


class SicknessHolidayDaysCalculations(ABC):
    def __init__(self, holidays_count: int, sickness_days_count: int, exceptional_break: int,
                 number_of_public_holidays: int, daily_working_hours: int, holiday_sickness_requests_dates: [str]):
        """
        @param holidays_count:
        @param sickness_days_count:
        @param number_of_public_holidays:
        @param daily_working_hours:
        """
        self.holidays_count = holidays_count
        self.sickness_days_count = sickness_days_count
        self.number_of_public_holidays = number_of_public_holidays
        self.daily_working_hours = daily_working_hours
        self.holiday_sickness_requests_dates = holiday_sickness_requests_dates
        self.exceptional_break = exceptional_break
        self.public_holidays = None

    def __str__(self):
        return "Explication: ( %.2f jours congés + %.2f jours maladie +%.2f congés exceptionnel )  x %d nombre h. /j " \
               "et %d jours fériés" % (
                   self.holidays_count,
                   self.sickness_days_count,
                   self.exceptional_break,
                   self.daily_working_hours,
                   self.number_of_public_holidays)

    def compute_total_hours(self):
        return (self.holidays_count + self.sickness_days_count + self.exceptional_break + self.number_of_public_holidays) * self.daily_working_hours

    def beautiful_explanation(self):
        _explanation = ""
        if self.sickness_days_count > 0:
            _explanation += "\nA été %d jour(s) en maladie. " % self.sickness_days_count
        if self.holidays_count > 0:
            _explanation += "\nA pris %d jour(s) de congés." % self.holidays_count
        if len(self.holiday_sickness_requests_dates) > 0:
            for holiday_sickness_r_date in self.holiday_sickness_requests_dates:
                _explanation += "\n du %s au %s" % (holiday_sickness_r_date.start_date, holiday_sickness_r_date.end_date)
        return _explanation


class TotalTimesheetCalculations(ABC):
    def __init__(self, total_hours, total_sundays, total_hours_during_public_holidays,
                 total_hours_holidays_absence_taken, total_hours_holidays_absence_taken_object,
                 total_legal_working_hours, ):
        self.list_of_public_holidays_worked = None
        self.list_of_sundays_worked = None
        self.total_hours = total_hours
        self.total_sundays = total_sundays
        self.total_hours_during_public_holidays = total_hours_during_public_holidays
        self.total_hours_holidays_absence_taken = total_hours_holidays_absence_taken
        self.total_hours_holidays_absence_taken_object = total_hours_holidays_absence_taken_object
        self.total_legal_working_hours = total_legal_working_hours

    def add_sunday_date_worked(self, sunday):
        if self.list_of_sundays_worked is None:
            self.list_of_sundays_worked = []
        self.list_of_sundays_worked.append(sunday)

    def add_public_holidays_date_worked(self, public_holiday):
        if self.list_of_public_holidays_worked is None:
            self.list_of_public_holidays_worked = []
        self.list_of_public_holidays_worked.append(public_holiday)
