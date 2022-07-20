# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys

from constance import config
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from invoices import settings
from invoices.employee import Employee
from invoices.enums.event import EventTypeEnum
from invoices.gcalendar2 import PrestationGoogleCalendarSurLu
from invoices.googlemessages import post_webhook
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


def limit_to_active_employees():
    return {'end_contract__isnull': True}


class Event(models.Model):
    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Event')
        ordering = ['-time_start_event']

    STATES = [
        (1, _('Waiting for validation')),
        (2, _('Valid')),
        (3, _('Done')),
        (4, _('Ignored')),
        (5, _('Not Done'))
    ]

    day = models.DateField(_('Event day'), help_text=_('Event day'))
    time_start_event = models.TimeField(_('Event start time'), blank=True, null=True,
                                        help_text=_('Event start time'))
    time_end_event = models.TimeField(_('Event end time'), blank=True, null=True, help_text=_('Event end time'))
    state = models.PositiveSmallIntegerField(_('State'), choices=STATES)
    event_type = models.ForeignKey(EventType, help_text=_('Event type'),
                                   on_delete=models.CASCADE,
                                   verbose_name=_('Event type'), blank=True, null=True)
    event_type_enum = models.CharField(_('Type'), max_length=10,
                                       choices=EventTypeEnum.choices, default=EventTypeEnum.CARE)
    employees = models.ForeignKey(Employee, related_name='event_link_to_employee', blank=True, null=True,
                                  help_text=_('Please select an employee'),
                                  on_delete=models.CASCADE, limit_choices_to=limit_to_active_employees)

    notes = models.TextField(
        _('Notes'),
        help_text=_('Notes'), blank=True, null=True)
    event_report = models.TextField(_('Rapport de soin'), help_text="A remplir une fois le soin terminé",
                                    blank=True, null=True)
    patient = models.ForeignKey(Patient, related_name='event_link_to_patient', blank=True, null=True,
                                help_text=_('Please select a patient'),
                                on_delete=models.CASCADE)
    at_office = models.BooleanField(_('At office premises'),
                                    help_text=_('Check the box if the event will occur at the office premises'),
                                    default=False)
    event_address = models.TextField(_('Event address'),
                                     help_text=_('Enter the address where the event will occur'),
                                     blank=True, null=True)
    created_by = models.CharField(max_length=30, default="ui")
    created_on = models.DateTimeField(default=timezone.now)
    calendar_url = models.URLField(blank=True, null=True, default='http://a.sur.lu')
    calendar_id = models.CharField(blank=True, null=True, default='0', max_length=100)

    def get_absolute_url(self):
        url = reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])
        if self.time_start_event:
            event_id = self.id
            cached_employees = cache.get('event_employees_cache_%s' % event_id)
            if not cached_employees:
                cache.set('event_employees_cache_%s' % event_id, self.employees)
                cached_employees = cache.get('event_employees_cache_%s' % event_id)
            return u'<a style="background-color:%s;color:%s;" class="eventtooltip" href="%s">%s %s</a>' % (
                cached_employees.color_cell,
                cached_employees.color_text,
                url,
                str(self),
                '<span class="evttooltiptext">chez: %s @ %s '
                '%s</span> '
                % (
                    self.patient,
                    self.time_start_event,
                    self.notes))
        return u'<a class="eventtooltip" href="%s">&#9829;%s %s</a>' % (url,
                                                                        str(self),
                                                                        '<span class="evttooltiptext">%s</span> '
                                                                        % self.notes)

    def clean(self, *args, **kwargs):
        exclude = []
        super(Event, self).clean_fields(exclude)
        messages = self.validate(self, self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)
        if self.at_office:
            self.event_address = "%s %s" % (config.NURSE_ADDRESS, config.NURSE_ZIP_CODE_CITY)
        cal = create_or_update_google_calendar(self)
        self.calendar_id = cal.get('id')
        self.calendar_url = cal.get('htmlLink')

    def delete(self, using=None, keep_parents=False):
        if EventTypeEnum.BIRTHDAY != self.event_type_enum:
            calendar_gcalendar = PrestationGoogleCalendarSurLu()
            # calendar_gcalendar.q_delete_event(self)
            calendar_gcalendar.delete_event(self)
        super(Event, self).delete(using=None, keep_parents=False)

    def display_unconnected_events(self):
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        # calendar_gcalendar.q_delete_event(self)
        inur_ids = calendar_gcalendar.list_event_with_sur_id()
        orphan_ids = []
        for found_event in inur_ids:
            if not Event.objects.filter(pk=found_event['inurId']):
                orphan_ids.append(found_event)
        print(orphan_ids)

    @staticmethod
    def validate(model, instance_id, data):
        result = {}
        # result.update(HolidayRequest.validate_dates(data))
        result.update(validate_date_range(instance_id, data))
        result.update(model.event_is_unique(data))
        # result.update(validators.validate_date_range_vs_timesheet(instance_id, data))
        # result.update(create_or_update_google_calendar(model))
        return result

    def event_is_unique(self, data):
        messages = {}
        events: QuerySet[Event] = Event.objects.filter(event_type=data["event_type_id"],
                                                       state=data["state"],
                                                       day=data["day"],
                                                       patient_id=data["patient_id"],
                                                       time_start_event=data["time_start_event"],
                                                       time_end_event=data["time_end_event"]).exclude(id=self.id)
        if events.count() > 0:
            messages = {'patient': 'Event already created'}
        return messages

    def print_html_safe_notes(self):
        if self.notes:
            return self.notes.replace('\r\n', '<br />').replace('\n', '<br />').replace('\r', '<br />')
        return ""

    def __str__(self):  # Python 3: def __str__(self):,
        cached_patient = cache.get('cached_patient_%s' % self.patient.id)
        if not cached_patient:
            cache.set('cached_patient_%s' % self.patient.id, self.patient)
            cached_patient = cache.get('cached_patient_%s' % self.patient.id)
        if self.event_type_enum not in [EventTypeEnum.CARE, EventTypeEnum.ASS_DEP]:
            return '%s for %s on %s' % (self.event_type_enum, cached_patient, self.day)
        cached_employees = cache.get('event_employees_cache_%s' % self.employees.id)
        if not cached_employees:
            cache.set('event_employees_cache_%s' % self.employees.id, self.employees)
            cached_employees = cache.get('event_employees_cache_%s' % self.employees.id)
        if self.event_assigned.count() > 1:
            return '%s ++ %s' % (
                ",".join(a.assigned_additional_employee.abbreviation for a in self.event_assigned.all()),
                cached_patient.name)
        return '%s - %s (%s)' % (cached_employees.abbreviation, cached_patient.name, self.event_type_enum)


class AssignedAdditionalEmployee(models.Model):
    class Meta:
        verbose_name = u'Invité Traitant'
        verbose_name_plural = u'Invités Traitant'

    assigned_additional_employee = models.ForeignKey(Employee, related_name='assigned_employees_to_event',
                                                     help_text='Please enter employee',
                                                     verbose_name=u"Soignant",
                                                     on_delete=models.CASCADE, null=True, blank=True, default=None)
    event_assigned_to = models.ForeignKey(Event, related_name='event_assigned',
                                          help_text='Please enter xxx',
                                          on_delete=models.CASCADE, null=True, blank=True, default=None)

    def __str__(self):
        return "%s - %s" % (self.assigned_additional_employee.abbreviation, self.event_assigned_to_id)


def create_or_update_google_calendar(instance):
    print("*** Creating event")
    sys.stdout.flush()
    if EventTypeEnum.GENERIC != instance.event_type_enum:
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        if instance.pk:
            old_event = Event.objects.get(pk=instance.pk)
            if old_event.employees != instance.employees:
                calendar_gcalendar.delete_event(old_event)
        return calendar_gcalendar.update_event(instance)


# @receiver(post_save, sender=Event, dispatch_uid="event_update_gcalendar_event")
# def create_or_update_google_calendar_callback(sender, instance, **kwargs):
#     print("*** Creating event from callback")
#     sys.stdout.flush()
#     create_or_update_google_calendar(instance)

@receiver(post_save, sender=Event, dispatch_uid="event_post_save")
def event_post_save_callback(sender, instance, **kwargs):
    if settings.GOOGLE_CHAT_WEBHOOK_URL:
        post_webhook(instance.employees, instance.patient, instance.event_report, instance.state)


@receiver(post_delete, sender=Event, dispatch_uid="event_delete_gcalendar_event")
def delete_google_calendar(sender, instance, **kwargs):
    if EventTypeEnum.GENERIC != instance.event_type_enum:
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        calendar_gcalendar.delete_event(instance)


def validate_date_range(instance_id, data):
    messages = {}
    conflicts_count = Event.objects.filter(day=data['day']).filter(
        Q(time_start_event__range=(data['time_start_event'], data['time_end_event'])) |
        Q(time_end_event__range=(data['time_start_event'], data['time_end_event'])) |
        Q(time_start_event__lte=data['time_start_event'], time_end_event__gte=data['time_start_event']) |
        Q(time_start_event__lte=data['time_end_event'], time_end_event__gte=data['time_end_event'])
    ).filter(
        employees_id=data['employees_id']).exclude(
        pk=instance_id).count()
    if 0 < conflicts_count:
        messages = {'time_start_event': _("Intersection with other %s") % Event._meta.verbose_name_plural}
    return messages
