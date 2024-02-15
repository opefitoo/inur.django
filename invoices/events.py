# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import os
from datetime import datetime as dt
from zoneinfo import ZoneInfo

import pytz
from constance import config
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q, QuerySet
from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dependence.detailedcareplan import MedicalCareSummaryPerPatientDetail
from invoices import settings
from invoices.employee import Employee
from invoices.enums.event import EventTypeEnum
from invoices.gcalendar2 import PrestationGoogleCalendarSurLu
from invoices.googlemessages import post_webhook, post_webhook_pic_as_image
from invoices.models import Patient, SubContractor
from invoices.notifications import send_email_notification


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
        (5, _('Not Done')),
        (6, _('Cancelled')),
    ]

    day = models.DateField(_('Event day'), help_text=_('Event day'))
    time_start_event = models.TimeField(_('Event start time'), blank=True, null=True,
                                        help_text=_('Event start time'))
    time_end_event = models.TimeField(_('Event end time'), blank=True, null=True, help_text=_('Event end time'))
    state = models.PositiveSmallIntegerField(_('State'), choices=STATES, default=2)
    event_type = models.ForeignKey(EventType, help_text=_('Event type'),
                                   on_delete=models.CASCADE,
                                   verbose_name=_('Event type'), blank=True, null=True)
    event_type_enum = models.CharField(_('Type'), max_length=10,
                                       choices=EventTypeEnum.choices, default=EventTypeEnum.CARE)
    employees = models.ForeignKey(Employee, related_name='event_link_to_employee', blank=True, null=True,
                                  help_text=_('Please select an employee'),
                                  on_delete=models.DO_NOTHING, limit_choices_to=limit_to_active_employees)
    sub_contractor = models.ForeignKey(SubContractor, related_name='event_link_to_sub_contractor',
                                       blank=True, null=True,
                                       help_text=_('Please select a sub contractor'),
                                       on_delete=models.DO_NOTHING)

    notes = models.TextField(
        _('Notes'),
        help_text=_('Notes'), blank=True, null=True)
    # link to CarePlanDetail
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
    updated_on = models.DateTimeField(auto_now=True)
    calendar_url = models.URLField(blank=True, null=True, default='http://a.sur.lu')
    calendar_id = models.CharField(blank=True, null=True, default='0', max_length=100)

    def add_report_picture(self, description, image):
        ReportPicture.objects.create(description=description, event=self, image=image)

    def get_admin_url(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        return reverse("admin:%s_%s_change" % (content_type.app_label, content_type.model), args=(self.id,))

    def is_in_validated_state(self):
        return self.state in [Event.STATES[2][0], Event.STATES[3][0], Event.STATES[4][0]]

    def duplicate_event_for_next_day(self, number_of_days=1):
        # duplicate event for next day
        # check if event already exists for next day
        # if not, duplicate event for next day
        # if yes, do nothing
        next_day = self.day + datetime.timedelta(days=number_of_days)
        if not Event.objects.filter(day=next_day, time_start_event=self.time_start_event,
                                    time_end_event=self.time_end_event, event_type=self.event_type,
                                    employees=self.employees, patient=self.patient).exists():
            employee_num_1 = Employee.objects.get(id=1)
            new_event = Event.objects.create(day=next_day, time_start_event=self.time_start_event,
                                             time_end_event=self.time_end_event,
                                             event_type_enum=self.event_type_enum,
                                             state=2, notes=self.notes,
                                             employees=employee_num_1,
                                             patient=self.patient,
                                             event_address=self.event_address,
                                             created_by='duplicate_event_for_next_day')
            # duplicate GenericTaskDescription
            for generic_task in self.generictaskdescription_set.all():
                new_generic_task = GenericTaskDescription.objects.create(event=new_event, name=generic_task.name)
                new_generic_task.save()
            # duplicate EventLinkToCareCode
            for care_code in self.eventlinktocarecode_set.all():
                new_event_link_to_care_code = EventLinkToCareCode.objects.create(event=new_event,
                                                                                 care_code=care_code.care_code)
                new_event_link_to_care_code.save()
            # duplicate EventLinkToMedicalCareSummaryPerPatientDetail
            for medical_care_summary in self.eventlinktomedicalcaresummaryperpatientdetail_set.all():
                new_event_link_to_medical_care_summary = EventLinkToMedicalCareSummaryPerPatientDetail.objects.create(
                    event=new_event,
                    medical_care_summary_per_patient_detail=medical_care_summary.medical_care_summary_per_patient_detail)
                new_event_link_to_medical_care_summary.save()
            new_event.save()
            return new_event
        else:
            return None

    def get_absolute_url(self):
        url = reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])
        event_text = str(self)
        if self.state in [Event.STATES[4][0], Event.STATES[5][0]]:
            event_text = "<del>%s</del>" % str(self)
        if self.time_start_event and self.employees:
            event_id = self.id
            cached_employees = cache.get('event_employees_cache_%s' % event_id)
            if not cached_employees:
                cache.set('event_employees_cache_%s' % event_id, self.employees)
                cached_employees = cache.get('event_employees_cache_%s' % event_id)
            return u'<a style="background-color:%s;color:%s;" class="eventtooltip" href="%s">%s %s</a>' % (
                cached_employees.color_cell,
                cached_employees.color_text,
                url,
                event_text,
                '<span class="evttooltiptext">chez: %s @ %s '
                '%s</span> '
                % (
                    self.patient,
                    self.time_start_event,
                    self.notes))
        if self.event_type_enum == EventTypeEnum.GENERIC:
            return u'<a class="eventtooltip" href="%s">&#9758;%s %s</a>' % (url,
                                                                            event_text,
                                                                            '<span class="evttooltiptext">%s</span> '
                                                                            % self.notes)

        return u'<a class="eventtooltip" href="%s">&#9829;%s %s</a>' % (url,
                                                                        event_text,
                                                                        '<span class="evttooltiptext">%s</span> '
                                                                        % self.notes)

    def clean(self):
        print(self.__dict__)
        print(self.data)
        cleaned_data = super().clean()
        print(cleaned_data)  # Add a print statement to see the cleaned data

    def clean(self, *args, **kwargs):
        exclude = []
        super(Event, self).clean_fields(exclude)
        messages = self.validate(self, self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)
        if self.at_office:
            self.event_address = "%s %s" % (config.NURSE_ADDRESS, config.NURSE_ZIP_CODE_CITY)
        else:
            cal = create_or_update_google_calendar(self)
            self.calendar_id = cal.get('id')
            self.calendar_url = cal.get('htmlLink')

    # FIXME pass date as parameter
    def cleanup_all_events_on_google(self, dry_run):
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        # calendar_gcalendar.q_delete_event(self)
        inur_ids = calendar_gcalendar.list_event_with_sur_id()
        deleted_evts = []
        for found_event in inur_ids:
            deleted_evts.append(calendar_gcalendar.delete_event_by_google_id(calendar_id=found_event['email'],
                                                                             event_id=found_event['gId'],
                                                                             dry_run=dry_run))
        return deleted_evts

    def display_unconnected_events(self):
        # FIXME not complete one
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        # calendar_gcalendar.q_delete_event(self)
        inur_ids = calendar_gcalendar.list_event_with_sur_id()
        orphan_ids = []
        events_different_times = []
        for found_event in inur_ids:
            # '2022-07-22T11:00:00Z'
            calendar_gcalendar.delete_event_by_google_id(calendar_id=found_event['email'],
                                                         event_id=found_event['gId'],
                                                         dry_run=True)
            lu_tz = pytz.timezone(found_event['start']['timeZone'])
            inur_event = Event.objects.get(pk=found_event['inurId'])
            try:
                localized_start = lu_tz.localize(
                    datetime.datetime.strptime(found_event['start']['dateTime'], '%Y-%m-%dT%H:%M:%SZ'))
                localized_end = lu_tz.localize(
                    datetime.datetime.strptime(found_event['end']['dateTime'], '%Y-%m-%dT%H:%M:%SZ'))
            except ValueError as v:
                print("%s %s" % (found_event['htmlLink'], found_event['start']['dateTime']))
                pass
                # localized_start = lu_tz.localize(
                #     datetime.datetime.strptime(found_event['start']['dateTime'], '%Y-%m-%dT%H:%M:%S-04:00'))
                # localized_end = lu_tz.localize(
                #     datetime.datetime.strptime(found_event['end']['dateTime'], '%Y-%m-%dT%H:%M:%S-04:00'))

            day_time_start_event = timezone.now().replace(year=inur_event.day.year, day=inur_event.day.day,
                                                          month=inur_event.day.month,
                                                          hour=inur_event.time_start_event.hour,
                                                          minute=inur_event.time_start_event.minute,
                                                          second=inur_event.time_start_event.second, microsecond=0)
            day_time_end_event = timezone.now().replace(year=inur_event.day.year, day=inur_event.day.day,
                                                        month=inur_event.day.month,
                                                        hour=inur_event.time_end_event.hour,
                                                        minute=inur_event.time_end_event.minute,
                                                        second=inur_event.time_end_event.second, microsecond=0)
            if not inur_event:
                orphan_ids.append(found_event)

            elif day_time_start_event != localized_start or day_time_end_event != localized_end:
                from dateutil.relativedelta import relativedelta
                offset1 = relativedelta(day_time_start_event, localized_start)
                offset2 = relativedelta(day_time_end_event, localized_end)
                if (day_time_start_event - localized_start).seconds > 14400 \
                        or (day_time_end_event - localized_end).seconds > 14400:
                    events_different_times.append(inur_event)
        print(orphan_ids)
        print(events_different_times)

    @staticmethod
    def validate(model, instance_id, data):
        result = {}
        # result.update(HolidayRequest.validate_dates(data))
        result.update(event_end_time_and_address_is_sometimes_mandatory(data))
        result.update(employee_maybe_mandatory(data))
        result.update(patient_maybe_mandatory(data))
        result.update(validate_date_range(instance_id, data))
        result.update(model.event_is_unique(data))
        result.update(address_mandatory_for_generic_employee(data))
        result.update(event_report_mandatory_validated_events(data))
        result.update(event_sub_contractor_mandatory_if_event_type_is_sub_care(data))
        # result.update(if_care_plan_check_date_times(data))
        # result.update(checks_that_care_plan_is_linked_to_right_patient(data))
        # result.update(validators.validate_date_range_vs_timesheet(instance_id, data))
        # result.update(create_or_update_google_calendar(model))
        return result

    def event_is_unique(self, data):
        messages = {}
        events: QuerySet[Event] = Event.objects.filter(event_type=data["event_type_id"],
                                                       state=data["state"],
                                                       day=data["day"],
                                                       patient_id=data["patient_id"],
                                                       employees_id=data["employees_id"],
                                                       time_start_event=data["time_start_event"],
                                                       time_end_event=data["time_end_event"]).exclude(pk=self.pk)
        # FIXME what a shame :(
        if events.count() == 1 and 'planning script' == events[0].created_by and not data['_state'].adding:
            return messages
        if events.count() > 0:
            messages = {'patient': 'Event already created'}
        return messages

    def print_html_safe_notes(self):
        if self.notes:
            return self.notes.replace('\r\n', '<br />').replace('\n', '<br />').replace('\r', '<br />')
        return ""

    def duration_in_hours(self):
        # Assuming both times are on the same day
        start_datetime = dt.combine(dt.today(), self.time_start_event)
        end_datetime = dt.combine(dt.today(), self.time_end_event)

        # Calculate duration
        duration_timedelta = end_datetime - start_datetime
        if duration_timedelta < datetime.timedelta(0):  # this checks if end is on the next day
            duration_timedelta += datetime.timedelta(days=1)

        # Convert to hours and return
        return duration_timedelta.seconds / 3600

    @property
    def fullname_state(self):
        return self.STATES[self.state - 1][1]

    def create_prestation_out_of_event(self, invoice_item):
        # create invoice item out of event
        from invoices.models import Prestation, CareCode
        prestations = Prestation.objects.filter(date__date=self.day, invoice_item__patient=self.patient,
                                                carecode=CareCode.objects.get(code='N307'))
        if prestations.count() > 0:
            return None
        # create 2 prestations
        p1 = Prestation.objects.create(invoice_item=invoice_item, date=self.day, employee=self.employees,
                                       carecode=CareCode.objects.get(code='NF01'))
        p2 = Prestation.objects.create(invoice_item=invoice_item, date=self.day, employee=self.employees,
                                       carecode=CareCode.objects.get(code='N307'))
        return p1, p2

    def __str__(self):  # Python 3: def __str__(self):,
        cached_patient = None
        if self.patient:
            cached_patient = cache.get('cached_patient_%s' % self.patient.id)
            if not cached_patient:
                cache.set('cached_patient_%s' % self.patient.id, self.patient)
                cached_patient = cache.get('cached_patient_%s' % self.patient.id)
        if self.event_type_enum == EventTypeEnum.BIRTHDAY:
            return '%s for %s on %s' % (self.event_type_enum, cached_patient, self.day)
        if self.event_type_enum == EventTypeEnum.GENERIC:
            return '%s for %s on %s' % (self.event_type_enum, cached_patient, self.day)
        if self.event_type_enum == EventTypeEnum.SUB_CARE:
            return '%s : %s for %s on %s' % (self.sub_contractor, self.event_type_enum, cached_patient, self.day)
        cached_employees = cache.get('event_employees_cache_%s' % self.employees.id)
        if not cached_employees:
            cache.set('event_employees_cache_%s' % self.employees.id, self.employees)
            cached_employees = cache.get('event_employees_cache_%s' % self.employees.id)
        if self.event_assigned.count() > 1:
            return '%s ++ %s' % (
                ",".join(a.assigned_additional_employee.abbreviation for a in self.event_assigned.all()),
                cached_patient.name)
        if cached_patient:
            return '%s - %s (%s)' % (cached_employees.abbreviation, str(cached_patient), self.event_type_enum)
        return '%s (%s)' % (cached_employees.abbreviation, self.event_type_enum)


class GenericTaskDescription(models.Model):
    class Meta:
        verbose_name = _('Generic Task Description')
        verbose_name_plural = _('Generic Task Descriptions')
        ordering = ['-id']

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(_('Descriptive Name'), max_length=50)
    # Additional fields for status and reason
    is_done = models.BooleanField(default=False, verbose_name=_("Is Done"))
    not_done_reason = models.TextField(blank=True, null=True, verbose_name=_("Reason if not done"))

    def __str__(self):  # Python 3: def __str__(self):,
        return '%s' % (self.name.strip())


class EventLinkToCareCode(models.Model):
    class Meta:
        verbose_name = _('Event -> Link to Care Code')
        verbose_name_plural = _('Event -> Link to Care Codes')
        ordering = ['-id']

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    care_code = models.ForeignKey('CareCode', on_delete=models.CASCADE)
    # Additional fields for status and reason
    is_done = models.BooleanField(default=False, verbose_name=_("Is Done"))
    not_done_reason = models.TextField(blank=True, null=True, verbose_name=_("Reason if not done"))

    def __str__(self):  # Python 3: def __str__(self):,
        return '%s - %s' % (self.event, self.care_code)


class EventLinkToMedicalCareSummaryPerPatientDetail(models.Model):
    class Meta:
        verbose_name = _('AEV')
        verbose_name_plural = _('AEVs')
        ordering = ['-id']

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    medical_care_summary_per_patient_detail = models.ForeignKey(MedicalCareSummaryPerPatientDetail,
                                                                on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(_('Quantity'), default=1)
    # Additional fields for status and reason
    is_done = models.BooleanField(default=False, verbose_name=_("Is Done"))
    not_done_reason = models.TextField(blank=True, null=True, verbose_name=_("Reason if not done"))

    def __str__(self):  # Python 3: def __str__(self):,
        return '%s - %s' % (self.event, self.medical_care_summary_per_patient_detail)


class EventGenericLink(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Additional fields for status and reason
    is_done = models.BooleanField(default=False, verbose_name=_("Is Done"))
    not_done_reason = models.TextField(blank=True, null=True, verbose_name=_("Reason if not done"))

    class Meta:
        unique_together = ('event', 'content_type', 'object_id')


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


def get_next_available_picture_name(path, file_prefixe, file_ext):
    filename = '%s_%04d%s' % (file_prefixe, 10000, file_ext)
    for i in range(1, 10000):
        filename = '%s_%04d%s' % (file_prefixe, i, file_ext)
        if not (default_storage.exists(os.path.join(path, filename))):
            break

    return filename


def update_report_picture_filename(instance, filename):
    if instance._get_pk_val():
        old = instance.__class__.objects.get(pk=instance._get_pk_val())
        if old and old.image.name:
            return old.image.name
    file_name, file_extension = os.path.splitext(filename)
    file_extension = file_extension.lower()
    if instance.event.day is None:
        _current_yr_or_prscr_yr = datetime.now().date().strftime('%Y')
        _current_month_or_prscr_month = datetime.now().date().strftime('%M')
    else:
        _current_yr_or_prscr_yr = str(instance.event.day.year)
        _current_month_or_prscr_month = str(instance.event.day.month)
    if instance.event.patient is None:
        path = os.path.join("Report Pictures",
                            "Sans patient",
                            _current_yr_or_prscr_yr, _current_month_or_prscr_month)
        file_prefix = 'Sans patient'
    else:
        path = os.path.join("Report Pictures",
                            instance.event.patient.name + ' ' +
                            instance.event.patient.first_name + ' ' +
                            instance.event.patient.code_sn,
                            _current_yr_or_prscr_yr, _current_month_or_prscr_month)

        file_prefix = '%s_%s_%s' % (instance.event.patient.name, instance.event.patient.first_name,
                                    str(instance.event.day))
    filename = get_next_available_picture_name(path, file_prefix, file_extension)

    return os.path.join(path, filename)


def validate_image(image):
    try:
        file_size = image.file.size
    except:
        return
    limit_kb = 10
    if file_size > limit_kb * 1024 * 1024:
        raise ValidationError("Taille maximale du fichier est %s MO" % limit_kb)


class ReportPicture(models.Model):
    class Meta:
        verbose_name = u'Image attachée au rapport'
        verbose_name_plural = u'Images attachées au rapport'

    description = models.TextField("Description",
                                   help_text='Please, give a description of the uploaded image.',
                                   max_length=250, default='')
    event = models.ForeignKey(Event, related_name='report_pictures',
                              help_text='Here, you can upload pictures if needed',
                              on_delete=models.CASCADE)
    image = models.ImageField(upload_to=update_report_picture_filename,
                              validators=[validate_image])


@receiver(post_delete, sender=ReportPicture, dispatch_uid="report_picture_clean_s3_post_delete")
def report_picture_clean_s3_post_delete(sender, instance, **kwargs):
    if instance.image.name:
        instance.image.delete(save=False)


class EventList(Event):
    class Meta:
        proxy = True
        verbose_name = "Mes tâches"
        verbose_name_plural = "Planning tâches à valider"


def create_or_update_google_calendar(instance):
    calendar_gcalendar = PrestationGoogleCalendarSurLu()
    if instance.pk:
        old_event = Event.objects.get(pk=instance.pk)
        if old_event.employees != instance.employees:
            calendar_gcalendar.delete_event(old_event)
    return calendar_gcalendar.update_event(instance)


@receiver(pre_save, sender=Event, dispatch_uid="event_pre_save_gcalendar")
def create_or_update_google_calendar_via_signal(sender, instance: Event, **kwargs):
    if settings.TESTING:
        print("** TEST mode")
        return
    calendar_gcalendar = PrestationGoogleCalendarSurLu()
    if instance.pk:
        old_event = Event.objects.get(pk=instance.pk)
        if old_event.employees != instance.employees:
            calendar_gcalendar.delete_event(old_event)
    gmail_event = calendar_gcalendar.update_event(instance)
    instance.calendar_id = gmail_event['id']
    instance.calendar_url = gmail_event['htmlLink']
    # instance.save()


@receiver(post_save, sender=Event, dispatch_uid="event_post_save_gcalendar")
def create_or_update_google_calendar_via_signal(sender, instance: Event, **kwargs):
    if settings.TESTING:
        print("** TEST mode")
        return
    calendar_gcalendar = PrestationGoogleCalendarSurLu()
    if instance.pk:
        print(calendar_gcalendar.update_events_sur_id(instance))
    if settings.GOOGLE_CHAT_WEBHOOK_URL:
        event_pictures_urls = None
        if instance.report_pictures.all():
            event_pictures_urls = ["%s|%s" % (a.image.url, a.description) if a.description else a.image.url
                                   for a in instance.report_pictures.all()]
        post_webhook(instance.employees, instance.patient, instance.event_report, instance.state,
                     event_date=datetime.datetime.combine(instance.day, instance.time_start_event).astimezone(
                         ZoneInfo("Europe/Luxembourg")), event_pictures_urls=event_pictures_urls, event=instance,
                     sub_contractor=instance.sub_contractor)
    if instance.event_type_enum == EventTypeEnum.SUB_CARE and instance.sub_contractor and instance.state == 2:
        # check if instance is new
        url = "%s%s " % (config.ROOT_URL, instance.get_admin_url())
        # send notification by email to sub-contractor
        if instance.sub_contractor.email_address:
            send_email_notification(
                subject='Nouveau soin en sous-traitance pour usager %s en date du %s ' % (
                instance.patient, instance.day),
                message='Bonjour, \n\n'
                        'Un nouveau soin en sous-traitance a été créé pour vous.\n\n'
                        'Vous pouvez le consulter ici : %s\n\n' % url +
                        'Cordialement,\n\n'
                        'Sur.lu',
                to_emails=[instance.sub_contractor.email_address],
            )


@receiver(post_save, sender=EventList, dispatch_uid="send_update_via_chat_1413")
def send_update_via_chat(sender, instance: EventList, **kwargs):
    if settings.TESTING:
        print("** TEST mode %s" % sender)
        return
    if settings.GOOGLE_CHAT_WEBHOOK_URL:
        event_pictures_urls = None
        if instance.report_pictures.all():
            event_pictures_urls = ["%s|%s" % (a.image.url, a.description) if a.description else a.image.url
                                   for a in instance.report_pictures.all()]
        post_webhook(instance.employees, instance.patient, instance.event_report, instance.state,
                     event_date=datetime.datetime.combine(instance.day, instance.time_start_event).astimezone(
                         ZoneInfo("Europe/Luxembourg")), event_pictures_urls=event_pictures_urls, event=instance,
                     sub_contractor=instance.sub_contractor)


@receiver(post_save, sender=ReportPicture, dispatch_uid="send_update_via_chat_via_report_picture_1710")
def send_update_via_chat(sender, instance: ReportPicture, **kwargs):
    if settings.TESTING:
        print("** TEST mode %s" % sender)
        return
    if settings.GOOGLE_CHAT_WEBHOOK_URL:
        # post_webhook_pic_urls(description=instance.description,
        #                      event_pictures_url=instance.image.url)
        email_of_employee = instance.event.employees.user.email
        if os.environ.get('LOCAL_ENV', None):
            print("Direct call post_save sneding update via chat %s" % instance)
            post_webhook_pic_as_image(description=instance.description,
                                      event_pictures_url=instance.image.url,
                                      email=email_of_employee)
        else:
            print("Call post_save on InvoiceItemBatch %s via redis /rq " % instance)
            post_webhook_pic_as_image.delay(description=instance.description,
                                            event_pictures_url=instance.image.url,
                                            email=email_of_employee)


# @receiver(post_save, sender=Event, dispatch_uid="event_update_gcalendar_event")
# def create_or_update_google_calendar_callback(sender, instance, **kwargs):
#     print("*** Creating event from callback")
#     sys.stdout.flush()
#     create_or_update_google_calendar(instance)


@receiver(pre_delete, sender=Event, dispatch_uid="event_delete_gcalendar_event")
def delete_google_calendar(sender, instance: Event, **kwargs):
    if settings.TESTING:
        print("** TEST mode")
        return
    if instance.calendar_id != 0:
        calendar_gcalendar = PrestationGoogleCalendarSurLu()
        calendar_gcalendar.delete_event(instance)


def event_end_time_and_address_is_sometimes_mandatory(data):
    messages = {}
    if data['event_type_enum'] != EventTypeEnum.BIRTHDAY and data['time_end_event'] is None:
        messages = {'time_end_event': _("Heure fin est obligatoire pour type %s") % _(data['event_type_enum'])}
    if data['event_type_enum'] != EventTypeEnum.BIRTHDAY and data['time_start_event'] is None:
        messages = {'time_start_event': _("Heure début est obligatoire pour type %s") % _(data['event_type_enum'])}
    return messages


def employee_maybe_mandatory(data):
    messages = {}
    if data['event_type_enum'] == EventTypeEnum.GNRC_EMPL and data['employees_id'] is None:
        messages = {'employees': _("Employees est obligatoire pour %s") % _(data['event_type_enum'])}
    return messages


def patient_maybe_mandatory(data):
    messages = {}
    if data['event_type_enum'] == EventTypeEnum.GENERIC and data['patient_id'] is None:
        messages = {'patient': _("Patient est obligatoire pour %s") % _(data['event_type_enum'])}
    return messages


def address_mandatory_for_generic_employee(data):
    messages = {}
    if data['event_type_enum'] == EventTypeEnum.GNRC_EMPL and len(data['event_address']) == 0 and not data['at_office']:
        messages = {'event_address': _("Adresse est obligatoire pour %s") % _(data['event_type_enum'])}
    return messages


def event_report_mandatory_validated_events(data):
    messages = {}
    if data['state'] in (3, 5) and (data['event_report'] is None or len(data['event_report']) == 0):
        messages = {'event_report': _("Rapport de soin obligatoire  lors d'une validation")}
    return messages


def event_sub_contractor_mandatory_if_event_type_is_sub_care(data):
    messages = {}
    if data['event_type_enum'] == EventTypeEnum.SUB_CARE and data['sub_contractor_id'] is None:
        messages = {'sub_contractor': _("Sous-traitant est obligatoire pour %s") % _(data['event_type_enum'])}
    if data['event_type_enum'] == EventTypeEnum.SUB_CARE and data['sub_contractor_id'] is not None:
        if data['employees_id'] is not None:
            messages = {'employees': _("champ Employé non autorisé car de type %s") % _(data['event_type_enum'])}
    if data['sub_contractor_id'] is not None and (
            data['event_type_enum'] is None or data['event_type_enum'] != EventTypeEnum.SUB_CARE):
        messages = {'event_type_enum': _("champ Type non autorisé car de type %s doit être de type %s") % (_(
            data['event_type_enum']), _(EventTypeEnum.SUB_CARE))}
    return messages


# def if_care_plan_check_date_times(data):
#     messages = {}
#     if data['event_type_enum'] == EventTypeEnum.ASS_DEP and data['care_plan_detail_id']:
#         assigned_care_plan = CarePlanDetail.objects.get(pk=data['care_plan_detail_id'])
#         if assigned_care_plan:
#             if data['time_start_event'] < assigned_care_plan.time_start:
#                 messages = {'time_start_event': _("Heure début doit être supérieur à %s car le plan est %s") % (
#                     assigned_care_plan.time_start, str(assigned_care_plan))}
#             if data['time_end_event'] > assigned_care_plan.time_end:
#                 messages = {'time_end_event': _("Heure fin doit être inférieur à %s car le plan est %s") % (
#                     assigned_care_plan.time_end, str(assigned_care_plan))}
#             # check if weekday is the same as care plan
#             if "*" not in assigned_care_plan.days_of_week() and data[
#                 'day'].weekday() in assigned_care_plan.days_of_week():
#                 messages = {'day': _("Jour doit être %s car le plan est %s") % (
#                     assigned_care_plan.get_day_of_week_display(), str(assigned_care_plan))}
#     return messages
#
#
# def checks_that_care_plan_is_linked_to_right_patient(data):
#     messages = {}
#     if data['event_type_enum'] == EventTypeEnum.ASS_DEP and data['care_plan_detail_id']:
#         assigned_care_plan = CarePlanDetail.objects.get(pk=data['care_plan_detail_id'])
#         if assigned_care_plan:
#             if CarePlanMaster.objects.get(patient_id=data['patient_id']) != assigned_care_plan.care_plan_to_master:
#                 messages = {'care_plan_detail': _(
#                     "Plan de soin doit être lié au patient, vous avez choisi le plan lié à %s") % (
#                                                     str(Patient.objects.get(
#                                                         pk=assigned_care_plan.care_plan_to_master.patient_id)))}
#     return messages


def validate_date_range(instance_id, data):
    messages = {}
    conflicts = None
    if data['state'] in [5, 6]:
        return messages
    if data['employees_id'] and data['time_start_event'] and data['time_end_event']:
        conflicts = Event.objects.filter(day=data['day']).filter(
            Q(time_start_event__range=(data['time_start_event'], data['time_end_event'])) |
            Q(time_end_event__range=(data['time_start_event'], data['time_end_event'])) |
            Q(time_start_event__lte=data['time_start_event'], time_end_event__gte=data['time_start_event']) |
            Q(time_start_event__lte=data['time_end_event'], time_end_event__gte=data['time_end_event'])
        ).filter(
            employees_id=data['employees_id']).exclude(
            pk=instance_id).exclude(state=Event.STATES[5][0]).exclude(state=Event.STATES[4][0])
    elif data['patient_id'] and data['employees_id'] is None:
        conflicts = Event.objects.filter(day=data['day']).filter(
            Q(time_start_event__range=(data['time_start_event'], data['time_end_event'])) |
            Q(time_end_event__range=(data['time_start_event'], data['time_end_event'])) |
            Q(time_start_event__lte=data['time_start_event'], time_end_event__gte=data['time_start_event']) |
            Q(time_start_event__lte=data['time_end_event'], time_end_event__gte=data['time_end_event'])
        ).filter(
            employees_id=data['patient_id']).exclude(
            pk=instance_id).exclude(state=Event.STATES[5][0]).exclude(state=Event.STATES[4][0])
    if conflicts and 0 < conflicts.count():
        messages = {'state': _("Intersection with other %s, here : %s from %s to %s") %
                             (Event._meta.verbose_name_plural, conflicts[0], conflicts[0].time_start_event,
                              conflicts[0].time_end_event)}
    return messages

# @receiver(post_save, sender=Patient, dispatch_uid="sync_future_events_adresses_when_patient_address_changed")
# def sync_future_events_addresses_when_patient_address_changed(sender, instance, **kwargs):
#     if instance.address is not None:
#         # get futures events for patient where event address is not set
#         future_events = Event.objects.filter(patient=instance, day__gte=timezone.now().date(),
#                                              event_address="")
#         for event in future_events:
#             event.address = instance.address
#             event.save()
