from abc import ABC


class SicknessHolidayDaysCalculations(ABC):
    def __init__(self, holidays_count: int, sickness_days_count: int, number_of_public_holidays: int,
                 daily_working_hours: int):
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

    def __str__(self):
        return "Explication: ( (%.2f jours congés + %.2f jours maladie) - %d jours fériés )  x %d nombre h. /j" % (
            self.holidays_count,
            self.sickness_days_count,
            self.number_of_public_holidays,
            self.daily_working_hours)

    def compute_total_hours(self):
        return ((self.holidays_count + self.sickness_days_count) - self.number_of_public_holidays) * self.daily_working_hours

    def beautiful_explanation(self):
        _explanation = ""
        if self.sickness_days_count > 0:
            _explanation += "A été %d jour(s) en maladie. " % self.sickness_days_count
        if self.holidays_count > 0:
            _explanation += "A pris %d jour(s) de congés." % self.holidays_count
        return _explanation

