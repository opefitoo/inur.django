from django.contrib.auth.models import User, Group
from django.utils import timezone
from rest_framework import serializers
from django_countries.serializers import CountryFieldMixin
from rest_framework.exceptions import ValidationError

from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization, \
    ValidityDate, InvoiceItemBatch
from invoices.timesheet import Timesheet, TimesheetTask
from invoices.employee import JobPosition


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class ValidityDateSerializer(serializers.ModelSerializer):
    def validate(self, data):
        instance_id = None
        if self.instance is not None:
            instance_id = self.instance.id
        messages = ValidityDate.validate(instance_id, data)
        if messages:
            raise serializers.ValidationError(messages)

        return data

    class Meta:
        model = ValidityDate
        fields = ('id', 'start_date', 'end_date', 'gross_amount', 'care_code')


class CareCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareCode
        depth = 1
        validity_dates = ValidityDateSerializer()
        fields = (
        'id', 'code', 'name', 'description', 'reimbursed', 'current_gross_amount', 'exclusive_care_codes', 'validity_dates')


class PatientSerializer(CountryFieldMixin, serializers.ModelSerializer):
    def validate(self, data):
        instance_id = None
        if self.instance is not None:
            instance_id = self.instance.id

        messages = Patient.validate(instance_id, data)
        if messages:
            raise serializers.ValidationError(messages)

        return data

    class Meta:
        model = Patient
        fields = ('code_sn', 'first_name', 'name', 'address', 'zipcode', 'city', 'country', 'phone_number',
                  'email_address', 'participation_statutaire', 'is_private')
        participation_statutaire = serializers.NullBooleanField(required=False)
        is_private = serializers.NullBooleanField(required=False)


class PhysicianSerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = Physician
        fields = (
            'id', 'provider_code', 'first_name', 'name', 'address', 'zipcode', 'city', 'country', 'phone_number',
            'fax_number', 'email_address')


class PrestationSerializer(serializers.ModelSerializer):
    def validate(self, data):
        instance_id = None
        if self.instance is not None:
            instance_id = self.instance.id
        messages = Prestation.validate(instance_id, data)
        if messages:
            raise serializers.ValidationError(messages)

        return data

    class Meta:
        model = Prestation
        fields = ('id', 'invoice_item', 'carecode', 'date', 'employee', 'quantity', 'at_home')


class MedicalPrescriptionSerializer(serializers.ModelSerializer):
    def validate(self, data):
        instance_id = None
        if self.instance is not None:
            instance_id = self.instance.id
        messages = MedicalPrescription.validate(instance_id, data)
        if messages:
            raise serializers.ValidationError(messages)

        return data

    class Meta:
        model = MedicalPrescription
        fields = ('id', 'prescriptor', 'patient', 'date', 'end_date', 'file')


class InvoiceItemSerializer(serializers.ModelSerializer):
    def validate(self, data):
        instance_id = None
        if self.instance is not None:
            instance_id = self.instance.id
        messages = InvoiceItem.validate(instance_id, data)
        if messages:
            raise serializers.ValidationError(messages)

        return data

    class Meta:
        model = InvoiceItem
        fields = ('id', 'invoice_number', 'accident_id', 'accident_date', 'invoice_date', 'patient_invoice_date',
                  'invoice_send_date', 'invoice_sent', 'invoice_paid', 'medical_prescription', 'patient', 'prestations',
                  'is_private')


class InvoiceItemBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItemBatch
        fields = ('id', 'start_date', 'end_date', 'send_date', 'payment_date', 'file')


class JobPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosition
        fields = ('id', 'name', 'description')


class TimesheetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timesheet
        fields = ('id', 'employee', 'start_date', 'end_date', 'submitted_date', 'other_details', 'timesheet_validated')


class TimesheetTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimesheetTask
        fields = ('id', 'name', 'description')


class HospitalizationSerializer(serializers.ModelSerializer):
    def validate(self, data):
        instance_id = None
        if self.instance is not None:
            instance_id = self.instance.id
        messages = Hospitalization.validate(instance_id, data)
        messages.update(Hospitalization.validate_date_range(instance_id, data))
        if messages:
            raise serializers.ValidationError(messages)

        return data

    class Meta:
        model = Hospitalization
        fields = ('id', 'start_date', 'end_date', 'description', 'patient')
