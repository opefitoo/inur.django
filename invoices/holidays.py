# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django_currentuser.db.models import CurrentUserField

from invoices.notifications import send_email_notification
from invoices.timesheet import SimplifiedTimesheetDetail, Employee


class HolidayRequest(models.Model):
    class Meta(object):
        verbose_name = u"Demande d'absence"
        verbose_name_plural = u"Demandes d'absence"
        constraints = [
            models.UniqueConstraint(fields=['employee', 'start_date', 'end_date'],
                                    name='unique holiday request')
        ]

    REASONS = [
        (1, u'Congés'),
        (2, u'Maladie'),
        (3, u'Formation'),
        (4, u'Desiderata')
    ]
    request_accepted = models.BooleanField(u"Demande acceptée", default=False, blank=True)
    validated_by = models.ForeignKey('invoices.Employee', related_name='validator',
                                     on_delete=models.CASCADE, blank=True,
                                     null=True)
    employee = CurrentUserField()
    start_date = models.DateField(u'Date début')
    end_date = models.DateField(u'Date fin')
    half_day = models.BooleanField(u"Demi journée")
    reason = models.PositiveSmallIntegerField(
        choices=REASONS)

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
        result.update(validate_date_range(instance_id, data))
        result.update(validate_date_range_vs_timesheet(instance_id, data))
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
    conflicts_count = HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], data['end_date'])) |
        Q(end_date__range=(data['start_date'], data['end_date'])) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
    ).filter(
        employee_id=data['employee_id']).exclude(
        pk=instance_id).count()
    if 0 < conflicts_count:
        messages = {'start_date': "Intersection avec d'autres demandes"}
    return messages


def validate_date_range_vs_timesheet(instance_id, data):
    messages = {}
    conflicts = SimplifiedTimesheetDetail.objects.filter(start_date__range=(data['start_date'], data['end_date']),
                                                         simplified_timesheet__employee__user_id=data['employee_id'])
    if 1 == conflicts.count():
        messages = {'start_date': u"Intersection avec des Temps de travail de : %s à %s" % (conflicts[0].start_date,
                                                                                            conflicts[0].end_date)}
    elif 1 < conflicts.count():
        messages = {'start_date': u"Intersection avec des Temps de travail de : %s à %s et %d autres conflits"
                                  % (conflicts[0].start_date, conflicts[0].end_date, conflicts.count() - 1)}

    return messages


@receiver(post_save, sender=HolidayRequest, dispatch_uid="notify_holiday_request_creation")
def notify_holiday_request_creation(sender, instance, created, **kwargs):
    if not created:
        return
    url = instance.get_admin_url()
    to_emails = []
    for em in Employee.objects.filter(occupation__name='administratrice'):
        to_emails.append(em.user.email)
    if len(to_emails) > 0:
        send_email_notification('A new holiday request from %s' % instance,
                                'please validate. %s' % url,
                                to_emails)
