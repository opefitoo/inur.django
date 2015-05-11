from ajax_select import LookupChannel

from models import Patient, CareCode
from django.utils.html import escape
from django.db.models.query_utils import Q


class PatientDuMoisLookup(LookupChannel):
    model = Patient

    def get_query(self, q, request):
        return Patient.objects.raw("select p.id, p.name, p.first_name " +
                                   "from public.invoices_patient p, public.invoices_prestation prest " +
                                   "where p.id = prest.patient_id " +
                                   # "where p.id = prest.patient_id and p.private_patient = 't'"+
                                   "and prest.date between '2014-12-01'::DATE and '2014-12-31'::DATE " +
                                   "and (select count(inv.id) from public.invoices_invoiceitem inv " +
                                   "where inv.invoice_date between '2014-12-01'::DATE and '2014-12-31'::DATE " +
                                   "and inv.patient_id = p.id) = 0 " +
                                   # or p.name like '%" + q + "%' "
                                   "group by p.id " +
                                   "order by p.name")

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


# TODO
class PrivatePatientDuMoisLookup(LookupChannel):
    model = Patient

    def get_query(self, q, request):
        pp = Patient.objects.raw("select p.id, p.name, p.first_name " +
                                       "from invoices_patient p, invoices_prestation prest " +
                                       "where p.private_patient ='t' " +
                                       "and prest.patient_id = p.id " +
                                       "and prest.id not in (select pp.prestation_id " +
                                       "from invoices_privateinvoiceitem priv, invoices_privateinvoiceitem_prestations pp group by pp.prestation_id) " +
                                       "group by p.id " +
                                       "order by p.name")
        q_result = []
        for p in pp:
            if q in p.name.lower() or q.lower() in p.first_name.lower():
                q_result.append(p)
        return q_result

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
