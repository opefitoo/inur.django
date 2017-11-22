from ajax_select import LookupChannel

from models import Patient, CareCode, Prestation, InvoiceItem, Physician
from timesheet import TimesheetTask
from django.utils.html import escape
from django.db.models.query_utils import Q
from django.utils.six import text_type
import json


class PatientDuMoisLookup(LookupChannel):
    model = Patient

    def get_query(self, q, request):
        queryset = Patient.objects.filter(Q(name__icontains=q) | Q(first_name__icontains=q))
        if 'is_private' in request.GET:
            is_private = json.loads(request.GET['is_private'])
            queryset = queryset.filter(Q(is_private=is_private))

        return queryset.order_by('name')

    def get_result(self, obj):
        u""" result is the simple text that is the completion of what the person typed """
        return obj.name

    def format_match(self, obj):
        """ (HTML) formatted item for display in the dropdown """
        return u"%s<div><i>%s</i></div>" % (escape(obj.name), escape(obj.first_name))
        # return self.format_item_display(obj)

    def format_item_display(self, obj):
        """ (HTML) formatted item for displaying item in the selected deck area """
        return u"%s<div><i>%s</i></div>" % (escape(obj.name), escape(obj.first_name))


class PhysicianLookup(LookupChannel):
    model = Patient

    def get_query(self, q, request):
        return Physician.objects.filter(Q(name__icontains=q) | Q(first_name__icontains=q)).order_by('name')

    def get_result(self, obj):
        u""" result is the simple text that is the completion of what the person typed """
        return obj.name

    def format_match(self, obj):
        """ (HTML) formatted item for display in the dropdown """
        return u"%s<div><i>%s</i></div>" % (escape(obj.name), escape(obj.first_name))
        # return self.format_item_display(obj)

    def format_item_display(self, obj):
        """ (HTML) formatted item for displaying item in the selected deck area """
        return u"%s<div><i>%s</i></div>" % (escape(obj.name), escape(obj.first_name))


class PatientLookup(LookupChannel):
    model = Patient

    def get_query(self, q, request):
        return Patient.objects.filter(Q(name__icontains=q) | Q(first_name__icontains=q)).order_by('name')

    def get_result(self, obj):
        u""" result is the simple text that is the completion of what the person typed """
        return obj.name

    def format_match(self, obj):
        """ (HTML) formatted item for display in the dropdown """
        return u"%s<div><i>%s</i></div>" % (escape(obj.name), escape(obj.first_name))
        # return self.format_item_display(obj)

    def format_item_display(self, obj):
        """ (HTML) formatted item for displaying item in the selected deck area """
        return u"%s<div><i>%s</i></div>" % (escape(obj.name), escape(obj.first_name))


class TimesheetTaskLookup(LookupChannel):

    model = TimesheetTask

    def get_query(self, q, request):
        return TimesheetTask.objects.filter(name__icontains=q).order_by('name')

    def get_result(self, obj):
        return text_type(obj)

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return "%s<div><i>%s</i></div>" % (escape(obj.name), escape(obj.description))

    def can_add(self, user, model):
        """ customize can_add by allowing anybody to add a Group.
            the superclass implementation uses django's permissions system to check.
            only those allowed to add will be offered a [+ add] popup link
            """
        return True


class CareCodeLookup(LookupChannel):
    model = CareCode

    def get_query(self, q, request):
        return CareCode.objects.filter(Q(code__istartswith=q) | Q(name__icontains=q)).order_by('code')

    def get_result(self, obj):
        u""" result is the simple text that is the completion of what the person typed """
        return obj.code

    def format_match(self, obj):
        """ (HTML) formatted item for display in the dropdown """
        return u"%s<div><i>%s</i></div>" % (escape(obj.code), escape(obj.name))
        # return self.format_item_display(obj)

    def format_item_display(self, obj):
        """ (HTML) formatted item for displaying item in the selected deck area """
        return u"%s<div><i>%s</i></div>" % (escape(obj.code), escape(obj.name))


class PrestationLookup(LookupChannel):
    model = Prestation

    def get_query(self, q, request):
        return Prestation.objects.filter(Q(patient__name__icontains=q) | Q(patient__first_name__icontains=q)).order_by('patient__name')

    def get_result(self, obj):
        u""" result is the simple text that is the completion of what the person typed """
        return str(obj)

    def format_match(self, obj):
        """ (HTML) formatted item for display in the dropdown """
        return u"%s<div><i>%s</i></div>" % (escape(str(obj.date)), escape(str(obj)))
        # return self.format_item_display(obj)

    def format_item_display(self, obj):
        """ (HTML) formatted item for displaying item in the selected deck area """
        return u"%s<div><i>%s</i></div>" % (escape(str(obj.date)), escape(str(obj)))


class InvoiceItemLookup(LookupChannel):
    model = InvoiceItem

    def get_query(self, q, request):
        return InvoiceItem.objects.filter(Q(invoice_number__istartswith=q) | Q(invoice_number__icontains=q)).order_by('invoice_number')

    def get_result(self, obj):
        u""" result is the simple text that is the completion of what the person typed """
        return obj.code

    def format_match(self, obj):
        """ (HTML) formatted item for display in the dropdown """
        return u"%s<div><i>%s</i></div>" % (escape(obj.code), escape(obj.name))
        # return self.format_item_display(obj)

    def format_item_display(self, obj):
        """ (HTML) formatted item for displaying item in the selected deck area """
        return u"%s<div><i>%s</i></div>" % (escape(obj.code), escape(obj.name))
