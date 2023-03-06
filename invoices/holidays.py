# -*- coding: utf-8 -*-
import os
from collections import namedtuple
from datetime import date, timedelta, datetime

from constance import config
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.timezone import now

from helpers.employee import get_admin_emails
from invoices.db.fields import CurrentUserField
from invoices.employee import Employee
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.notifications import send_email_notification
from invoices.validators import validators


class HolidayRequest(models.Model):
    class Meta(object):
        verbose_name = u"Demande d'absence"
        verbose_name_plural = u"Demandes d'absence"
        constraints = [
            models.UniqueConstraint(fields=['employee', 'start_date', 'end_date'],
                                    name='unique holiday request')
        ]

    # FIXME replace by ENUM
    REASONS = [
        (1, u'Congés'),
        (2, u'Maladie'),
        (3, u'Formation'),
        (4, u'Desiderata'),
        (5, u'Exceptionnel')
    ]

    # TODO replace by builtin enums
    # https://stackoverflow.com/questions/54802616/how-to-use-enums-as-a-choice-field-in-django-model
    # HOLIDAY_WORKFLOW = [
    #     (0, u'En attente de validation'),
    #     (1, u'Refusé'),
    #     (2, u'Validé'),
    # ]
    validator_notes = models.TextField(
        'Notes Validateur',
        help_text='Notes', blank=True, null=True)

    request_status = models.CharField(
        max_length=4,
        choices=HolidayRequestWorkflowStatus.choices,
        default=HolidayRequestWorkflowStatus.PENDING)
    validated_by = models.ForeignKey(Employee, related_name='validator',
                                     on_delete=models.CASCADE, blank=True,
                                     null=True)
    # FIXME rename to user, not employee
    employee = CurrentUserField()
    request_creator = CurrentUserField(related_name='holiday_request_creator')
    force_creation = models.BooleanField(default=False, help_text=u"Si vous êtes manager vous pouvez forcer la "
                                                                  "création de congés même si conflits avec d#autre "
                                                                  "employés")
    do_not_notify = models.BooleanField(default=False, help_text="Do not send email notifications",
                                        blank=True, null=True, verbose_name="Do not notify")
    start_date = models.DateField(u'Date début')
    end_date = models.DateField(u'Date fin')
    requested_period = models.CharField("Période",
                                        max_length=4,
                                        choices=HolidayRequestChoice.choices,
                                        default=HolidayRequestChoice.req_full_day)
    reason = models.PositiveSmallIntegerField(
        choices=REASONS)

    @property
    def hours_taken(self):
        # import holidays
        # lu_holidays = holidays.Luxembourg()
        # counter = 0
        # delta = self.end_date - self.start_date
        # date_comp = self.start_date
        # jours_feries = 0
        # if self.reason > 1:
        #     return "Non applicable"
        # for i in range(delta.days + 1):
        #     if date_comp.weekday() < 5 and self.requested_period != HolidayRequestChoice.req_full_day:
        #         counter += 0.5
        #     elif date_comp.weekday() < 5 and self.requested_period == HolidayRequestChoice.req_full_day:
        #         counter += 1
        #     if date_comp in lu_holidays:
        #         jours_feries = jours_feries + 1
        #     date_comp = date_comp + timedelta(days=1)
        # if Employee.objects.get(user_id=self.employee.id).employeecontractdetail_set.filter(
        #         start_date__lte=self.start_date).first() is None:
        #     return "définir les heures de travail contractuels svp."
        # hours_jour = Employee.objects.get(user_id=self.employee.id).employeecontractdetail_set.filter(
        #     start_date__lte=self.start_date).first().number_of_hours / 5
        computation = self.hours_calculations(holiday_request=self)
        if isinstance(computation, str) or "Non applicable" == computation:
            return computation
        return [(computation.num_days - computation.jours_feries) * computation.hours_jour,
                "explication: ( (%.2f jours congés + %.2f jours maladie ) - %d jours fériés )  x %d nombre h. /j" % (
                    computation.num_days,
                    computation.num_days_sickness,
                    computation.jours_feries,
                    computation.hours_jour)]

    def hours_calculations(self, same_year_only=False, holiday_request=None):
        import holidays
        lu_holidays = holidays.Luxembourg()
        # if holiday end date is before employee start_contract date then return 0
        if holiday_request.end_date < Employee.objects.get(user_id=holiday_request.employee.id).start_contract:
            Computation = namedtuple('Computation', 'num_days num_days_sickness hours_jour jours_feries')
            computation = Computation(0, 0, 0, 0)
            return computation
        counter_holidays = 0
        counter_sickness_leaves = 0
        if same_year_only and holiday_request.end_date.year != holiday_request.start_date.year:
            delta = holiday_request.end_date.replace(year=holiday_request.start_date.year, month=12,
                                                     day=31) - holiday_request.start_date
        else:
            delta = holiday_request.end_date - holiday_request.start_date
        date_comp = holiday_request.start_date
        jours_feries = 0
        if holiday_request.reason > 2:
            return "Non applicable"
        if holiday_request.reason == 1:
            for i in range(delta.days + 1):
                if date_comp.weekday() < 5 and holiday_request.requested_period != HolidayRequestChoice.req_full_day:
                    counter_holidays += 0.5
                elif date_comp.weekday() < 5 and holiday_request.requested_period == HolidayRequestChoice.req_full_day:
                    counter_holidays += 1
                if date_comp in lu_holidays:
                    jours_feries = jours_feries + 1
                date_comp = date_comp + timedelta(days=1)
        elif holiday_request.reason == 2:
            for i in range(delta.days + 1):
                if date_comp.weekday() < 5 and holiday_request.requested_period != HolidayRequestChoice.req_full_day:
                    counter_sickness_leaves += 0.5
                elif date_comp.weekday() < 5 and holiday_request.requested_period == HolidayRequestChoice.req_full_day:
                    counter_sickness_leaves += 1
                if date_comp in lu_holidays:
                    jours_feries = jours_feries + 1
                date_comp = date_comp + timedelta(days=1)

        employee_contract_details = Employee.objects.get(
            user_id=holiday_request.employee.id).employeecontractdetail_set.filter(
            start_date__lte=holiday_request.start_date, end_date__isnull=True)
        if employee_contract_details.count() > 1:
            raise Exception("More than one contract for employee when calculating holiday request %s" % (holiday_request, holiday_request.id))
        if employee_contract_details.count() == 0:
            employee_contract_details = Employee.objects.get(
                user_id=holiday_request.employee.id).employeecontractdetail_set.filter(
                start_date__lte=holiday_request.start_date, end_date__gte=holiday_request.start_date)

            if employee_contract_details.count() == 0:
                # for employees who have a contract than ended before the start date of the holiday request
                employee_contract_details = Employee.objects.get(
                    user_id=holiday_request.employee.id).employeecontractdetail_set.filter(
                    start_date__lte=holiday_request.start_date, end_date__lte=holiday_request.start_date).order_by("-end_date")
                if employee_contract_details.count() == 0:
                    raise Exception("No contract for employee when calculating holiday request %s id %s" % (holiday_request, holiday_request.id))
            if employee_contract_details.count() > 1:
                raise Exception("More than one contract for this employee %s for holiday request %s" % (holiday_request.employee, holiday_request))
        if employee_contract_details.count() == 0:
            raise Exception("No contract for this employee %s for holiday request %s" % (holiday_request.employee, holiday_request))
        hours_jour = employee_contract_details.first().number_of_hours / 5

        Computation = namedtuple('Computation', 'num_days num_days_sickness hours_jour jours_feries')
        computation = Computation(counter_holidays, counter_sickness_leaves, hours_jour, jours_feries)
        return computation

    @property
    def total_days_in_current_year(self):
        holidays_taken_same_year = HolidayRequest.objects.filter(start_date__year=self.start_date.year,
                                                                 request_status=HolidayRequestWorkflowStatus.ACCEPTED,
                                                                 employee=self.employee,
                                                                 reason=self.REASONS[0][0])
        calculation = 0
        for holiday_req in holidays_taken_same_year:
            calculation += holiday_req.hours_calculations(same_year_only=True, holiday_request=holiday_req).num_days
        return calculation

    @property
    def total_hours_off_available(self, year=None):
        """
        For a specific year, returns the number of hours off available for the employee.
        :return: the number of hours off available for the employee
        @return:
        """
        if year is None:
            year = self.start_date.year
        # if employee contract detail end date is None or at least one contract detail date end is after the year
        # we are looking for, we can assume that the employee is still working for the company
        if Employee.objects.get(user_id=self.employee.id).employeecontractdetail_set.filter(
                end_date__isnull=True).exists() or \
                Employee.objects.get(user_id=self.employee.id).employeecontractdetail_set.filter(
                    end_date__year=year).exists():
            hours_off_available = 0
            # if self.start_date.year equals year then for month in range to as of now
            # else for month in range 1 to 12
            if self.start_date.year == year:
                #
                for month in range(1, self.end_date.month + 1):
                    hours_off_available += self.hours_off_available_per_month(month, year)
            else:
                for month in range(1, 13):
                    hours_off_available += self.hours_off_available_per_month(month, year)
            return hours_off_available

    def hours_off_available_per_month(self, month, year):
        """
        For a specific month and year, returns the number of hours off available for the employee.
        @param month:
        @param year:
        @return:
        """
        hours_off_available = 0
        employee_contract_details = Employee.objects.get(
            user_id=self.employee.id).employeecontractdetail_set.filter(
            start_date__lte=datetime(year, month, 1), end_date__isnull=True).first()
        if employee_contract_details is None:
            employee_contract_details = Employee.objects.get(
                user_id=self.employee.id).employeecontractdetail_set.filter(
                start_date__lte=datetime(year, month, 1), end_date__gt=datetime(year=year, month=month, day=1)).first()
        if employee_contract_details is not None:
            number_of_hours_off_for_the_month = employee_contract_details.number_of_hours * 0.43333333333333335
            hours_off_available += number_of_hours_off_for_the_month
            # round to 2 decimals commercial
            return round(hours_off_available, 2)
        else:
            return 0

    def clean(self, *args, **kwargs):
        exclude = []

        super(HolidayRequest, self).clean_fields(exclude)
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(HolidayRequest.validate_dates(data))
        if not (User.objects.get(id=data['request_creator_id']).is_superuser and data['force_creation']):
            result.update(validate_date_range(instance_id, data))
        if data['start_date'] > date.today() and not (User.objects.get(id=data['request_creator_id']).is_superuser
                                                      and data['force_creation']):
            # only if it is in the future if date is the past no intersection validation is done
            result.update(validate_requests_from_other_employees(instance_id, data))
        result.update(validators.validate_date_range_vs_timesheet(instance_id, data))
        result.update(validators.validate_full_day_request(data))
        return result

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['start_date'] <= data['end_date']
        if not is_valid:
            messages = {'end_date': 'End date must be bigger than Start date'}
        return messages

    def get_admin_url(self):
        info = (self._meta.app_label, self._meta.model_name)
        return reverse('admin:%s_%s_change' % info, args=(self.pk,))

    def __str__(self):
        return u'%s de %s - du  %s au %s' % (
            self.REASONS[self.reason - 1][1], self.employee, self.start_date, self.end_date)


def update_absence_request_filename(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.request.start_date is None:
        _current_yr_or_prscr_yr = now().date().strftime('%Y')
        _current_month_or_prscr_month = now().date().strftime('%M')
    else:
        _current_yr_or_prscr_yr = str(instance.request.start_date.year)
        _current_month_or_prscr_month = str(instance.request.start_date.month)
    path = os.path.join("Doc. Demandes Absences", _current_yr_or_prscr_yr,
                        _current_month_or_prscr_month)
    filename = '%s%s' % (str(instance.request), file_extension)

    return os.path.join(path, filename)


class AbsenceRequestFile(models.Model):
    request = models.ForeignKey(HolidayRequest, on_delete=models.CASCADE)
    file_description = models.CharField("description", max_length=30)
    file_upload = models.FileField(null=True, blank=True, upload_to=update_absence_request_filename)


def validate_date_range(instance_id, data):
    messages = {}
    if data['force_creation'] or data['reason'] > 1:
        return messages
    conflicts = HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], data['end_date'])) |
        Q(end_date__range=(data['start_date'], data['end_date'])) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
    ).filter(reason=1, request_status=HolidayRequestWorkflowStatus.ACCEPTED).exclude(pk=instance_id)
    if 0 < conflicts.count():
        messages = {'start_date': "Intersection avec d'autres demandes %s " % conflicts[0]}
    return messages


def validate_requests_from_other_employees(instance_id, data):
    messages = {}
    if data['force_creation']:
        return messages
    conflicts = HolidayRequest.objects.filter(
        end_date__lte=data['end_date'], end_date__gte=data['start_date']) | \
                HolidayRequest.objects.filter(start_date__gte=data['start_date'], start_date__lte=data['end_date'])
    conflicts = conflicts.filter(request_status=HolidayRequestWorkflowStatus.ACCEPTED).filter(reason=1).exclude(
        employee_id=data['employee_id']).exclude(pk=instance_id)
    if 0 < conflicts.count():
        for conflict in conflicts:
            messages = {"start_date": u"149 Intersection avec d'autres demandes de %s" % conflict}
    return messages


@receiver(post_save, sender=HolidayRequest, dispatch_uid="notify_holiday_request_creation")
def notify_holiday_request_creation(sender, instance, created, **kwargs):
    if not created:
        return
    url = "%s%s " % (config.ROOT_URL, instance.get_admin_url())
    to_emails = get_admin_emails()
    if len(to_emails) > 0:
        send_email_notification('A new %s' % instance,
                                'please validate. %s' % url,
                                to_emails)
