# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from invoices.employee import Employee


class YaleAuthToken(models.Model):
    class Meta:
        app_label = 'invoices'
        verbose_name = _('Door Event')
        verbose_name_plural = _('Door Events')
        ordering = ['-id']
    token = models.JSONField()
    created_by = models.CharField(max_length=30, default="ui")
    created_on = models.DateTimeField(default=timezone.now)


class DoorEvent(models.Model):
    class Meta:
        app_label = 'invoices'
        verbose_name = _('Door Event')
        verbose_name_plural = _('Door Events')
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'activity_start_time', 'activity_end_time', 'activity_type'],
                                    name='unique door event')
        ]

    employee = models.ForeignKey(Employee, related_name='door_event_link_to_employee', blank=True, null=True,
                                 help_text=_('Please select an employee'),
                                 on_delete=models.CASCADE)
    activity_start_time = models.DateTimeField()
    activity_end_time = models.DateTimeField()
    action = models.CharField(max_length=30, default="action")
    activity_type = models.CharField(max_length=40)
    created_by = models.CharField(max_length=30, default="ui")
    created_on = models.DateTimeField(default=timezone.now)

    def __str__(self):  # Python 3: def __str__(self):
        return "%s %s - %s" % (self.employee, self.activity_type, self.activity_start_time)


def get_last_yale_token():
    if len(YaleAuthToken.objects.all()) > 0:
        return YaleAuthToken.objects.first().token
    return None


def token_saver(token):
    YaleAuthToken.objects.all().delete()
    YaleAuthToken(token=token).save()
