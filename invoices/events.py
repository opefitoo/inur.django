# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from invoices.employee import Employee
from invoices.gcalendar2 import PrestationGoogleCalendarSurLu
from invoices.models import Patient


class EventType(models.Model):
    class Meta:
        verbose_name = _('Event -> Type')
        verbose_name_plural = _('Event -> Types')
        ordering = ['-id']

    name = models.CharField(_('Descriptive Name'), max_length=50)
    to_be_generated = models.BooleanField(_('To be generated'),
                                          help_text=_('If checked, these type of events types will be generated auto.'),
                                          default=False)

    @staticmethod
    def autocomplete_search_fields():
        return 'name'

    def __str__(self):  # Python 3: def __str__(self):,
        return '%s' % (self.name.strip())


class Event(models.Model):
    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Event')
        ordering = ['-id']

    STATES = [
        (1, _('Waiting for validation')),
        (2, _('Valid')),
        (3, _('Done')),
        (4, _('Ignored'))
    ]

    day = models.DateField(_('Event day'), help_text=_('Event day'))
    time_start_event = models.TimeField(_('Event start time'), blank=True, null=True,
                                        help_text=_('Event start time'))
    time_end_event = models.TimeField(_('Event end time'), blank=True, null=True, help_text=_('Event end time'))
    state = models.PositiveSmallIntegerField(_('State'), choices=STATES)
    event_type = models.ForeignKey(EventType, blank=True, null=True,
                                   help_text=_('Event type'),
                                   on_delete=models.SET_NULL,
                                   verbose_name=_('Event type'))
    employees = models.ForeignKey(Employee, related_name='event_link_to_employee', blank=True, null=True,
                                  help_text=_('Please select an employee'),
                                  on_delete=models.CASCADE)
    notes = models.TextField(
        _('Notes'),
        help_text=_('Notes'), blank=True, null=True)
    patient = models.ForeignKey(Patient, related_name='event_link_to_patient', blank=True, null=True,
                                help_text=_('Please select a patient'),
                                on_delete=models.CASCADE)

    def get_absolute_url(self):
        url = reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])
        if self.time_start_event:
            return u'<a class="eventtooltip" href="%s">%s %s</a>' % (url,
                                                                     str(self),
                                                                     '<span class="evttooltiptext">chez: %s @ %s '
                                                                     '%s</span> '
                                                                     % (
                                                                         self.patient,
                                                                         self.time_start_event,
                                                                         self.notes))
        return u'<a class="eventtooltip" href="%s">%s %s</a>' % (url,
                                                                 str(self),
                                                                 '<span class="evttooltiptext">%s '
                                                                 '%s</span> '
                                                                 % (self.notes))

    def __str__(self):  # Python 3: def __str__(self):,
        if 'soin' != self.event_type.name:
            return '%s for %s on %s' % (self.event_type, self.patient, self.day)
        return '%s - %s' % (self.employees.user.first_name, self.patient.name)


@receiver(pre_save, sender=Event, dispatch_uid="event_update_gcalendar_event")
def create_or_update_google_calendar(sender, instance, **kwargs):
    if "soin" == instance.event_type.name:
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        if instance.pk:
            old_event = Event.objects.get(pk=instance.pk)
            if old_event.employees != instance.employees:
                calendar_gcalendar.delete_event(old_event)
        calendar_gcalendar.update_event(instance)


@receiver(post_delete, sender=Event, dispatch_uid="event_delete_gcalendar_event")
def delete_google_calendar(sender, instance, **kwargs):
    if "soin" == instance.event_type.name:
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        calendar_gcalendar.delete_event(instance)
