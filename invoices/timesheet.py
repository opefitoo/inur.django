# -*- coding: utf-8 -*-
import calendar
from datetime import date, datetime, timedelta
from typing import Any, Union

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from helpers.holidays import how_many_hours_taken_in_period_v2
from helpers.timesheet import calculate_total_hours, display_in_hours_minutes_value
from invoices.db.fields import CurrentUserField
from invoices.employee import Employee
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus


class Timesheet(models.Model):
    class Meta:
        ordering = ['-id']

    employee = models.ForeignKey(Employee,
                                 on_delete=models.CASCADE)
    start_date = models.DateField('Date debut')
    start_date.editable = True
    end_date = models.DateField('Date fin')
    end_date.editable = True
    submitted_date = models.DateTimeField("Date d'envoi", blank=True,
                                          null=True)
    submitted_date.editable = True
    other_details = models.TextField(u"Autres détails", max_length=100, blank=True,
                                     null=True)
    timesheet_validated = models.BooleanField("Valide", default=False)

    def __str__(self):  # Python 3: def __str__(self):
        return '%s - du %s au %s' % (self.employee, self.start_date, self.end_date)


class TimesheetTask(models.Model):
    class Meta:
        ordering = ['-id']

    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100, blank=True,
                                   null=True)

    @staticmethod
    def autocomplete_search_fields():
        return 'name'

    def __str__(self):  # Python 3: def __str__(self):
        return '%s' % (self.name.strip())


class TimesheetDetail(models.Model):
    start_date = models.DateTimeField('Date')
    end_date = models.TimeField('Heure fin')
    task_description = models.ManyToManyField(TimesheetTask, verbose_name='Description(s) tache',
                                              help_text="Entrez une ou plusieurs taches.")
    patient = models.ForeignKey('invoices.Patient',
                                on_delete=models.CASCADE)
    timesheet = models.ForeignKey(Timesheet,
                                  on_delete=models.CASCADE)
    other = models.CharField(max_length=50, blank=True, null=True)

    def clean(self):
        exclude = []
        if self.patient is not None and self.patient.id is None:
            exclude = ['patient']
        # if self.task_description is not None:
        #    exclude.append('task_description')
        if self.timesheet is not None and self.timesheet.id is None:
            exclude.append('timesheet')

        super(TimesheetDetail, self).clean_fields(exclude)

        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(TimesheetDetail.validate_dates(data))
        return result

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['start_date'].time() <= data['end_date']
        if not is_valid:
            messages = {'end_date': u"Heure de fin doit être supérieure à l'heure de début"}

        return messages

    def __str__(self):
        return ''


def current_month():
    return date.today().month


def current_year():
    return date.today().year


def max_value_current_year(value):
    return MaxValueValidator(current_year())(value)


class SimplifiedTimesheet(models.Model):
    class Meta(object):
        verbose_name = u'Temps de travail'
        verbose_name_plural = u'Temps de travail'
        constraints = [
            models.UniqueConstraint(fields=['employee', 'time_sheet_year', 'time_sheet_month'],
                                    name='unique time sheet')
        ]

    timesheet_validated = models.BooleanField("Valide", default=False)
    employee = models.ForeignKey('invoices.Employee',
                                 on_delete=models.CASCADE)
    employee.editable = False
    employee.visible = False
    time_sheet_year = models.PositiveIntegerField(
        default=current_year())
    user = CurrentUserField()
    user.visible = False
    extra_hours_paid_current_month = models.DecimalField(u"Heures supp. payées ou récupérées pour le mois courant",
                                                         default=0,
                                                         max_digits=4,
                                                         decimal_places=2
                                                         )
    extra_hours_balance = models.DecimalField(u"Balance des heures supp. non soldées",
                                              help_text="Ce champ est calculé mais vous pouvez quand même écraser la valeur si vous êtes admin.\n"
                                                        "Il reporte le total des heures suppl. (ou déficit) du mois M - 1.\n"
                                                        "Il est (re)calculé à chaque fois que l'on valide un Temps de Travail et la formule : Hours should work TS(M-1) + Balance des heures supp. non soldées - Heures supp. payées ou récupérées pour le mois courant",
                                              default=0,
                                              max_digits=5,
                                              decimal_places=2)

    YEARS_MONTHS = [
        (1, u'Janvier'),
        (2, u'Février'),
        (3, u'Mars'),
        (4, u'Avril'),
        (5, u'Mai'),
        (6, u'Juin'),
        (7, u'Juillet'),
        (8, u'Août'),
        (9, u'Septembre'),
        (10, u'Octobre'),
        (11, u'Novembre'),
        (12, u'Décembre'),
    ]
    time_sheet_month = models.PositiveSmallIntegerField(
        choices=YEARS_MONTHS,
        default=current_month(),
    )

    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __calculate_total_hours(self):
        if self.id:
            calculated_hours = cache.get('total_hours_dictionary%s' % self.id)
            if calculated_hours is not None:
                return calculated_hours
        calculated_hours = {"total": 0,
                            "total_sundays": 0,
                            "total_public_holidays": 0,
                            "total_hours_holidays_taken": [0, ""]}
        total = timezone.timedelta(0)
        total_sundays = timezone.timedelta(0)
        total_public_holidays = timezone.timedelta(0)
        for v in self.simplifiedtimesheetdetail_set.all():
            delta = datetime.combine(timezone.now(), v.end_date) - \
                    datetime.combine(timezone.now(), v.start_date.astimezone().time().replace(tzinfo=None))
            total = total + delta
            if v.start_date.astimezone().weekday() == 6:
                total_sundays = total_sundays + delta
            if PublicHolidayCalendarDetail.objects.filter(
                    calendar_date__exact=v.start_date.astimezone()).first() is not None:
                total_public_holidays = total_public_holidays + delta
        calculated_hours["total_hours_holidays_taken"] = self.absence_hours_taken()
        calculated_hours["total_hours_holidays_taken_verbose"] = "%d heure(s) --> %s" % (
            calculated_hours["total_hours_holidays_taken"][0],
            str(calculated_hours["total_hours_holidays_taken"][1]))
        calculated_hours["total"] = total
        calculated_hours["total_sundays"] = total_sundays
        calculated_hours["total_public_holidays"] = total_public_holidays
        if self.id:
            cache.set('total_hours_dictionary%s' % self.id, calculated_hours)
        return calculated_hours

    def absence_hours_taken(self):
        data = {'start_date': self.get_start_date, 'end_date': self.get_end_date, 'user_id': self.user.id}
        return how_many_hours_taken_in_period_v2(data,
                                                 PublicHolidayCalendarDetail.objects.filter(
                                                     calendar_date__lte=data['end_date'],
                                                     calendar_date__gte=data['start_date']))

    @property
    def total_hours_holidays_taken(self):
        return self.__calculate_total_hours()["total_hours_holidays_taken_verbose"]

    @property
    def total_hours_holidays_and_sickness_taken(self):
        return self.__calculate_total_hours()["total_hours_holidays_taken"]

    @property
    def hours_should_work_gross_in_sec(self):
        calculated_hours = self.__calculate_total_hours()
        total_legal_working_hours = self.date_range(self.get_start_date, self.get_end_date) * \
                                    ((self.employee.employeecontractdetail_set.filter(Q(
                                        end_date__gte=self.get_end_date, start_date__lte=self.get_start_date) | Q(
                                        end_date__isnull=True,
                                        start_date__lte=self.get_start_date)).first().number_of_hours / 5))
        balance: Union[float, Any] = calculated_hours["total"].total_seconds() + \
                                     (calculated_hours["total_hours_holidays_taken"][
                                          0] - total_legal_working_hours) * 3600
        return balance

    @property
    def hours_should_work(self):
        if self.id:
            calculated_hours = cache.get('total_hours_dictionary%s' % self.id)
            if calculated_hours is None:
                calculated_hours = self.__calculate_total_hours()
        total_legal_working_hours = self.date_range(self.get_start_date, self.get_end_date) * \
                                    ((self.employee.employeecontractdetail_set.filter(Q(
                                        end_date__gte=self.get_end_date, start_date__lte=self.get_start_date) | Q(
                                        end_date__isnull=True,
                                        start_date__lte=self.get_start_date)).first().number_of_hours / 5))
        balance: Union[float, Any] = calculated_hours["total"].total_seconds() + \
                                     (calculated_hours["total_hours_holidays_taken"][
                                          0] - total_legal_working_hours) * 3600
        # return "%d h:%d mn" % (balance // 3600, (balance % 3600) // 60)
        return "%.2f heures(s)" % round(balance / 3600, 2)

    @staticmethod
    def date_range(start_date, end_date):
        if not start_date and not end_date:
            return
        days = 0
        for i in range(0, calendar.monthrange(start_date.year, start_date.month)[1]):
            next_date = start_date + timedelta(i)
            if next_date.weekday() not in (5, 6):
                days = days + 1
        for i in PublicHolidayCalendarDetail.objects.filter(calendar_date__lte=end_date, calendar_date__gte=start_date):
            if i.calendar_date.weekday() not in (5, 6):
                days = days - 1
        return days

    @property
    def total_working_days(self):
        return "Jours ouvrables %d, Heures contractuelles %d (h/semaine)" % (
            self.date_range(self.get_start_date, self.get_end_date),
            (self.employee.employeecontractdetail_set.filter(Q(
                end_date__gte=self.get_end_date, start_date__lte=self.get_start_date) | Q(
                end_date__isnull=True,
                start_date__lte=self.get_start_date)).first().number_of_hours))

    # FIXME this is deprecated use new one
    def total_hours_xxx(self):
        total_delta = self.__calculate_total_hours()["total"].total_seconds()
        return "%d h:%d mn" % (total_delta // 3600, (total_delta % 3600) // 60)

    @property
    def total_hours(self):
        return display_in_hours_minutes_value(total_seconds=calculate_total_hours(self).total_hours.total_seconds())

    # FIXME deprecated to be removed
    def total_hours_sundays_xxx(self):
        return self.__calculate_total_hours()["total_sundays"]

    @property
    def total_hours_sundays(self):
        return "%s (%s)" % (display_in_hours_minutes_value(total_seconds=
                                                           calculate_total_hours(self).total_sundays.total_seconds()),
                            calculate_total_hours(self).list_of_sundays_worked)

    # FIXME deprecated to be removed
    @property
    def total_hours_public_holidays_xxx(self):
        return self.__calculate_total_hours()["total_public_holidays"]

    @property
    def total_hours_public_holidays(self):
        return "%s (%s)" % (display_in_hours_minutes_value(total_seconds=
                                                           calculate_total_hours(self).total_hours_during_public_holidays.total_seconds()),
                            calculate_total_hours(self).list_of_public_holidays_worked)

    #
    # @property
    # def total_holiday_hours(self):
    #     start_date = timezone.now().replace(year=self.time_sheet_year, month=self.time_sheet_month, day=1)
    #     end_date = timezone.now().replace(year=self.time_sheet_year,
    #                                       month=self.time_sheet_month,
    #                                       day=calendar.monthrange(self.time_sheet_year, self.time_sheet_month)[1])
    #     HolidayRequest.objects.filter(
    #         Q(start_date__range=start_date, end_date))
    #     ).filter(
    #         employee_id=employee_id).filter(request_accepted=True)

    def clean(self):
        exclude = []

        if hasattr(self, 'employee') and self.employee is not None and self.employee.id is None:
            exclude.append('employee')

        super(SimplifiedTimesheet, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance, data):
        result = {}
        result.update(SimplifiedTimesheet.validate_one_per_year_month(instance, data))
        return result

    @staticmethod
    def validate_one_per_year_month(instance, data):
        messages = {}
        conflicts_count = SimplifiedTimesheet.objects.filter(
            time_sheet_year=data['time_sheet_year']). \
            filter(time_sheet_month=data['time_sheet_month']). \
            filter(employee__user_id=data['user_id']). \
            exclude(pk=instance.id).count()
        if 0 < conflicts_count:
            messages.update({'time_sheet_year':
                                 "Il y a déjà un Temps de travail pour cette année et ce mois dans le système"})
            messages.update({'time_sheet_month':
                                 "Il y a déjà un Temps de travail pour cette année et ce mois dans le système"})
        return messages

    @property
    def get_start_date(self):
        return datetime(self.time_sheet_year, self.time_sheet_month, 1)

    @property
    def get_end_date(self):
        return datetime(self.time_sheet_year, self.time_sheet_month,
                        calendar.monthrange(self.time_sheet_year, self.time_sheet_month)[1])

    def __str__(self):  # Python 3: def __str__(self):
        return u'%s - du  %s au %s' % (self.employee, self.get_start_date, self.get_end_date)


class SimplifiedTimesheetDetail(models.Model):
    start_date = models.DateTimeField('Date')
    end_date = models.TimeField('Heure fin')
    simplified_timesheet = models.ForeignKey(SimplifiedTimesheet,
                                             on_delete=models.CASCADE)

    class Meta(object):
        verbose_name = u'Détail temps de travail'
        verbose_name_plural = u'Détails temps de travail'

    def time_delta(self):
        if self.end_date:
            return datetime.combine(timezone.now(), self.end_date) - \
                   datetime.combine(timezone.now(), self.start_date.astimezone().time().replace(tzinfo=None))
        else:
            return 0

    def clean(self):
        exclude = []

        if self.simplified_timesheet is not None and self.simplified_timesheet.id is None:
            exclude.append('simplified_timesheet')

        super(SimplifiedTimesheetDetail, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance, data):
        result = {}
        result.update(SimplifiedTimesheetDetail.validate_dates(data))
        result.update(SimplifiedTimesheetDetail.validate_periods(instance.simplified_timesheet.time_sheet_month,
                                                                 instance.simplified_timesheet.time_sheet_year, data))
        result.update(validate_date_range_vs_holiday_requests(data, instance.simplified_timesheet.user.id))
        return result

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['start_date'].time() <= data['end_date']
        if not is_valid:
            messages = {'end_date': u"Heure de fin doit être avant l'heure de début"}

        return messages

    @staticmethod
    def validate_periods(month, year, data):
        messages = {}
        is_valid = data['start_date'].month == month and data['start_date'].year == year
        if not is_valid:
            messages = {'start_date': u"Date doit être dans le mois %d de l'année %s" % (month, year)}

        return messages

    def __str__(self):
        return ''


class PublicHolidayCalendar(models.Model):
    calendar_year = models.PositiveIntegerField(
        default=current_year())

    def __str__(self):
        return u"Congés publics pour l'année: %d" % self.calendar_year


class PublicHolidayCalendarDetail(models.Model):
    calendar_date = models.DateField(u'Date calendrier',
                                     help_text=u'Saisir la date calendrier du jour férié')
    calendar_link = models.ForeignKey(PublicHolidayCalendar, on_delete=models.CASCADE)

    def clean(self):
        exclude = []

        if self.calendar_link is not None and self.calendar_link.id is None:
            exclude.append('calendar_link')

        super(PublicHolidayCalendarDetail, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance, data):
        result = {}
        result.update(PublicHolidayCalendarDetail.validate_same_year(data, instance.calendar_link.calendar_year))
        return result

    @staticmethod
    def validate_same_year(data, year):
        messages = {}
        is_valid = data['calendar_date'] is None or data['calendar_date'].year == year
        if not is_valid:
            messages = {'calendar_date': u"Veuillez saisir des dates pour l'année %s" % year}
        return messages

    def __str__(self):
        return "%s - %s" \
               % (date(self.calendar_date.year, self.calendar_date.month, self.calendar_date.day).strftime("%A"),
                  self.calendar_date)


def validate_date_range_vs_holiday_requests(data, employee_id):
    msgs = {}
    from invoices.holidays import HolidayRequest
    end_date_time = data['start_date']
    end_date_time.replace(hour=data['end_date'].hour, minute=data['end_date'].minute)
    conflicts = HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], end_date_time)) |
        Q(end_date__range=(data['start_date'], end_date_time)) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=end_date_time, end_date__gte=end_date_time)
    ).filter(employee_id=employee_id, request_status=HolidayRequestWorkflowStatus.ACCEPTED)
    if 1 == conflicts.count():
        conflict = conflicts[0]
        if conflict.requested_period == HolidayRequestChoice.req_full_day:
            msgs = {'start_date': u"Intersection avec des demandes d'absence de : %s à %s" % (conflicts[0].start_date,
                                                                                              conflicts[0].end_date)}
        elif (conflict.requested_period == HolidayRequestChoice.req_morning
              and data['start_date'].time() < data['start_date'].time().replace(hour=12, minute=0, second=0)) \
                or (conflict.requested_period == HolidayRequestChoice.req_evening
                    and data['end_date'] > data['start_date'].time().replace(hour=12, minute=0, second=0)):
            msgs = {
                'start_date': u"Intersection avec des demandes d'absence de : %s à %s" % (conflicts[0].start_date,
                                                                                          conflicts[0].end_date)}

    elif 1 < conflicts.count():
        msgs = {'start_date': u"Intersection avec des demandes d'absence de : %s à %s et %d autres conflits"
                              % (conflicts[0].start_date, conflicts[0].end_date, conflicts.count() - 1)}

    return msgs


@receiver(post_save, sender=SimplifiedTimesheet, dispatch_uid="notify_timesheet_refresh_cache")
def notify_timesheet_refresh_cache(sender, instance, created, **kwargs):
    cache.clear()
    print(cache)
