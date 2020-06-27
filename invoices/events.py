# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.urls import reverse
from invoices.models import Patient


class EventType(models.Model):
    class Meta:
        verbose_name = u'Événements -> Type'
        verbose_name_plural = u'Événements -> Type'
        ordering = ['-id']

    name = models.CharField(max_length=50)
    
    @staticmethod
    def autocomplete_search_fields():
        return 'name'

    def __str__(self):  # Python 3: def __str__(self):,
        return '%s' % (self.name.strip())


class Event(models.Model):
    class Meta:
        verbose_name = u'Événements'
        verbose_name_plural = u'Événements'

    STATES = [
        (1, u'En attente de validation'),
        (2, u'Validé'),
        (3, u'Traité'),
        (4, u'Ignoré')
    ]

    day = models.DateField(u'Jour de l''événement', help_text=u'Jour de l''événement')
    state = models.PositiveSmallIntegerField(choices=STATES)
    event_type = models.ForeignKey(EventType, blank=True, null=True,
                                   help_text='Type d''événement', on_delete=models.SET_NULL)
    notes = models.TextField(
        u'Notes', help_text=u'Notes', blank=True, null=True)
    patient = models.ForeignKey(Patient, related_name='Patient', blank=True, null=True,
                                help_text='Veuillez séléctionner un patient',
                                on_delete=models.CASCADE)
    def get_absolute_url(self):
        url = reverse('admin:%s_%s_change' % (self._meta.app_label, self._meta.model_name), args=[self.id])
        return u'<a href="%s">%s</a>' % (url, str(self.day))


