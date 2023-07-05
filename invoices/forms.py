from datetime import datetime

from django import forms
from django.forms import BaseInlineFormSet, ValidationError, ModelForm
from django.utils import timezone
from django_select2.forms import ModelSelect2Widget

from dependence.careplan import CarePlanDetail
from invoices.events import Event
from invoices.models import InvoiceItem, MedicalPrescription
from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail
from invoices.widgets import CodeSnWidget, ContaboImageWidget


def check_for_periods_intersection(cleaned_data):
    for row_index, row_data in enumerate(cleaned_data):
        is_valid = True
        for index, data in enumerate(cleaned_data):
            if index == row_index:
                continue

            if row_data['start_date'] >= data['start_date'] and data['end_date'] is None:
                is_valid = False
            elif data['end_date'] is not None:
                if data['start_date'] <= row_data['start_date'] <= data['end_date']:
                    is_valid = False
                if row_data['end_date'] is not None:
                    if data['start_date'] <= row_data['end_date'] <= data['end_date']:
                        is_valid = False

        if not is_valid:
            raise ValidationError('Dates periods should not intersect')


def check_for_periods_intersection_time_based(cleaned_data):
    extra_cleaned_data = list(filter(None, cleaned_data))
    for row_index, row_data in enumerate(extra_cleaned_data):
        is_valid = True
        dates_on_error = set()
        for index, data in enumerate(extra_cleaned_data):
            if index == row_index:
                continue
            elif row_data['start_date'].date() != data['start_date'].date():
                continue
            elif row_data['DELETE']:
                continue
            elif not (row_data['start_date'].time() > data['end_date']
                      or row_data['end_date'] < data['start_date'].time()):
                dates_on_error.add(data['start_date'].date().strftime("%d/%m/%Y"))
                is_valid = False

        if not is_valid:
            raise ValidationError('Dates periods should not intersect : %s' % dates_on_error)


class ValidityDateFormSet(BaseInlineFormSet):
    def clean(self):
        super(ValidityDateFormSet, self).clean()

        if hasattr(self, 'cleaned_data'):
            check_for_periods_intersection(self.cleaned_data)


class PrestationInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super(PrestationInlineFormSet, self).clean()
        from invoices.models import InvoiceItemPrescriptionsList
        medical_prescription_list = InvoiceItemPrescriptionsList.objects.filter(invoice_item=self.instance).all()
        if hasattr(self, 'cleaned_data'):
            # self.validate_only_one_prescription_per_invoice(medical_prescriptions)
            self.validate_max_limit(self.cleaned_data)
            self.validate_palliative_care_only(self.cleaned_data)
            self.validate_no_duplicate_carecode_perday(self.cleaned_data)
            self.validate_prestations_inbetween_prescription_dates(self.cleaned_data, medical_prescription_list)
    @staticmethod
    def validate_only_one_prescription_per_invoice(medical_prescriptions):
        if len(medical_prescriptions) > 1:
            raise ValidationError(
                "There should be only one prescription per invoice, please create another invoice for %s" % medical_prescriptions[1].medical_prescription)


    @staticmethod
    def validate_no_duplicate_carecode_perday(cleaned_data):
        # if the same carecode is used more than once in the same day, raise an error
        # Collect dates and items seen as we go through the formset
        dates_seen = set()
        items_seen = set()
        for row_data in cleaned_data:
            if 'DELETE' in row_data and row_data['DELETE']:
                continue
            date = row_data['date']
            item = row_data['carecode'].code
            if (date, item) in items_seen:
                raise ValidationError(
                    "The same carecode %s was used more than once in the same day %s" % (item, date))
            else:
                dates_seen.add(date)
                items_seen.add((date, item))

    @staticmethod
    def validate_palliative_care_only(cleaned_data):
        palliative_care = False
        non_palliative_care = False
        non_palliative_care_code = None
        for row_data in cleaned_data:
            if 'DELETE' in row_data and row_data['DELETE']:
                continue
            if row_data['carecode'].code == "FSP2":
                palliative_care = True
            else:
                non_palliative_care = True
                non_palliative_care_code = row_data['carecode']
        if palliative_care and non_palliative_care:
            raise ValidationError(
                "Prestations should be either only Palliative Care or only Non Palliative Care in the same InvoiceItem, please create another invoice for %s" % non_palliative_care_code)
    @staticmethod
    def validate_prestations_inbetween_prescription_dates(cleaned_data, medical_prescription_list):
        # if the same carecode is used more than once in the same day, raise an error
        # Collect dates and items seen as we go through the formset
        if not medical_prescription_list or len(medical_prescription_list) == 0:
            return
        for row_data in cleaned_data:
            if 'DELETE' in row_data and row_data['DELETE']:
                continue
            date = row_data['date'].date()
            item = row_data['carecode'].code
            check_success = False
            for mls in medical_prescription_list:
                if mls.medical_prescription.end_date is None:
                    raise ValidationError(
                        "The prescription %s has no end date, please set an end date" % mls.medical_prescription)
                if mls.medical_prescription.date <= date <= mls.medical_prescription.end_date:
                    check_success = True
                else:
                    pass
            if not check_success:
                raise ValidationError(
                    "The date %s of item %s is not in between the prescription dates" % (date, item))


    @staticmethod
    def validate_max_limit(cleaned_data):
        expected_count = 0
        at_home_added = False
        for row_data in cleaned_data:
            if 'DELETE' in row_data and row_data['DELETE']:
                expected_count -= 1
            else:
                expected_count += 1
                if not at_home_added and 'at_home' in row_data and row_data['at_home']:
                    at_home_added = True
                    expected_count += 1

        if expected_count > InvoiceItem.PRESTATION_LIMIT_MAX:
            message = "Max number of Prestations for one InvoiceItem is %s" % (str(InvoiceItem.PRESTATION_LIMIT_MAX))
            raise ValidationError(message)


class SimplifiedTimesheetForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.timesheet_validated:
            for k, v in self.fields.items():
                v.disabled = True

    class Meta:
        model = SimplifiedTimesheet
        fields = '__all__'
        help_texts = {'total_hours': "Nombre total d'heures",
                      'total_hours_sundays': "Nombre total d'heures travaillées les Dimanche + la liste des dimanches",
                      'total_hours_public_holidays': "Nombre total d'heures travaillées les Jours fériés + la liste "
                                                     "de ces jours",
                      'hours_should_work': "si heures supp. alors le symbole + sinon avec le symble - devant le "
                                           "nombre d'heures "
                      }


class SimplifiedTimesheetDetailForm(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'simplified_timesheet') and self.instance.simplified_timesheet.timesheet_validated:
            for k, v in self.fields.items():
                v.disabled = True

    class Meta:
        model = SimplifiedTimesheetDetail
        fields = '__all__'

    def clean(self):
        super(SimplifiedTimesheetDetailForm, self).clean()
        all_clean_data = []
        for form in self.forms:
            if len(form.errors) == 0:
                all_clean_data.append(form.cleaned_data)
        check_for_periods_intersection_time_based(all_clean_data)


class InvoiceItemForm(forms.ModelForm):
    medical_prescription = forms.ModelChoiceField(
        queryset=MedicalPrescription.objects.all(),
        label=u"Medical Prescription",
        help_text=u"Entrez les première lettres du nom (ou prénom) du patient ou du docteur ou code CNS du médecin",
        required=False,
        widget=ModelSelect2Widget(
            search_fields=['patient__name__icontains',
                           'patient__first_name__icontains',
                           'prescriptor__name__icontains',
                           'prescriptor__first_name__icontains',
                           'prescriptor__provider_code__icontains'],
            dependent_fields={'patient': 'patient'},
        )
    )



class AlternateAddressFormSet(BaseInlineFormSet):
    def clean(self):
        super(AlternateAddressFormSet, self).clean()
        if hasattr(self, 'cleaned_data'):
            check_for_periods_intersection(self.cleaned_data)
class HospitalizationFormSet(BaseInlineFormSet):
    def clean(self):
        super(HospitalizationFormSet, self).clean()

        if hasattr(self, 'cleaned_data'):
            check_for_periods_intersection(self.cleaned_data)
            if 'date_of_death' in self.data and self.data['date_of_death']:
                date_of_death = datetime.strptime(self.data['date_of_death'], "%d/%m/%Y").date()
                self.validate_with_patient_date_of_death(self.cleaned_data, date_of_death)

    @staticmethod
    def validate_with_patient_date_of_death(cleaned_data, date_of_death):
        for row_data in cleaned_data:
            if row_data['end_date'] > date_of_death:
                raise ValidationError("Hospitalization cannot be later than or include Patient's death date")


class PatientForm(ModelForm):
    code_sn = forms.CharField(widget=CodeSnWidget())

    def __init__(self, *args, **kwargs):
        super(PatientForm, self).__init__(*args, **kwargs)


class EmployeeSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            option['attrs']['data-abbreviation'] = value.instance.abbreviation
        return option


def cannot_validate_in_future(instance, user):
    if user.is_superuser:
        return
    datetime_event_end = timezone.now().replace(year=instance.day.year,
                                                month=instance.day.month,
                                                day=instance.day.day,
                                                # FIXME: do not hard code
                                                hour=instance.time_end_event.hour - 2,
                                                minute=instance.time_end_event.minute)
    if timezone.now() < datetime_event_end:
        raise ValidationError(
            "Vous ne voupez pas valider un soin dans le futur "
        )
    return


class EventForm(ModelForm):
    care_plan_detail = forms.ModelChoiceField(queryset=CarePlanDetail.objects.all(), required=False,
                                              label="Plan de soin", to_field_name="id", )

    class Meta:
        model = Event
        exclude = ('event_type',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(EventForm, self).__init__(*args, **kwargs)

        if self.instance.at_office:
            self.fields['event_address'].disabled = True

    def clean(self):
        super().clean()
        cannot_validate_in_future(self.instance, self.request.user)


class MedicalPrescriptionForm(ModelForm):
    class Meta:
        model = MedicalPrescription()
        exclude = ()
        widgets = {'thumbnail_img': ContaboImageWidget()}
        readonly_fields = ('thumbnail_img',)

    thumbnail_img = forms.ImageField(widget=ContaboImageWidget(attrs={'readonly': 'readonly'}), label='Aperçu')
    thumbnail_img.required = False

    def __init__(self, *args, **kwargs):
        super(MedicalPrescriptionForm, self).__init__(*args, **kwargs)
