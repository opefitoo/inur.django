# -*- coding: utf-8 -*-
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django_currentuser.db.models import CurrentUserField

from helpers.employee import get_admin_emails
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
        (4, u'Desiderata')
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
        import holidays
        lu_holidays = holidays.Luxembourg()
        counter = 0
        delta = self.end_date - self.start_date
        date_comp = self.start_date
        jours_feries = 0
        if self.reason > 1:
            return "Non applicable"
        for i in range(delta.days + 1):
            if date_comp.weekday() < 5 and self.requested_period != HolidayRequestChoice.req_full_day:
                counter += 0.5
            elif date_comp.weekday() < 5 and self.requested_period == HolidayRequestChoice.req_full_day:
                counter += 1
            if date_comp in lu_holidays:
                jours_feries = jours_feries + 1
            date_comp = date_comp + timedelta(days=1)
        hours_jour = Employee.objects.get(user_id=self.employee.id).employeecontractdetail_set.filter(
            start_date__lte=self.start_date).first().number_of_hours / 5
        return [(counter - jours_feries) * hours_jour,
                "explication: ( %.2f jours congés - %d jours fériés )  x %d nombre h. /j" % (counter,
                                                                                           jours_feries,
                                                                                           hours_jour)]

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
        return u'%s - %s du  %s au %s' % (
            self.employee, self.REASONS[self.reason - 1][1], self.start_date, self.end_date)


def validate_date_range(instance_id, data):
    messages = {}
    conflicts = HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], data['end_date'])) |
        Q(end_date__range=(data['start_date'], data['end_date'])) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
    ).filter(reason=1, request_status=HolidayRequestWorkflowStatus.ACCEPTED).exclude(pk=instance_id)
    if 0 < conflicts.count():
        messages = {'start_date': "136 Intersection avec d'autres demandes %s " % conflicts[0]}
    return messages


def validate_requests_from_other_employees(instance_id, data):
    messages = {}
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
    url = instance.get_admin_url()
    to_emails = get_admin_emails()
    if len(to_emails) > 0:
        send_email_notification('A new holiday request from %s' % instance,
                                'please validate. %s' % url,
                                to_emails)
