from abc import ABC


class SicknessHolidayDaysCalculations(ABC):
    def __init__(self, holidays_count: int, sickness_days_count: int, number_of_public_holidays: int,
                 daily_working_hours: int, holiday_sickness_requests_dates: [str]):
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

    def __str__(self):
        return "Explication: ( %.2f jours congés + %.2f jours maladie )  x %d nombre h. /j et %d jours fériés" % (
            self.holidays_count,
            self.sickness_days_count,
            self.daily_working_hours,
            self.number_of_public_holidays)

    def compute_total_hours(self):
        return ((self.holidays_count + self.sickness_days_count) - self.number_of_public_holidays) * self.daily_working_hours

    def compute_total_hours_v2(self):
        return (self.holidays_count + self.sickness_days_count) * self.daily_working_hours

    def beautiful_explanation(self):
        _explanation = ""
        if self.sickness_days_count > 0:
            _explanation += "\nA été %d jour(s) en maladie. " % self.sickness_days_count
        if self.holidays_count > 0:
            _explanation += "\nA pris %d jour(s) de congés." % self.holidays_count
        if len(self.holiday_sickness_requests_dates) > 0:
            for holiday_sickness_r_date in self.holiday_sickness_requests_dates:
                _explanation += "\n %s" % holiday_sickness_r_date
        return _explanation

