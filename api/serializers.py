from django.contrib.auth.models import User, Group
from rest_framework import serializers
from django_countries.serializers import CountryFieldMixin
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization
from invoices.timesheet import JobPosition, Timesheet, TimesheetTask


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class CareCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareCode
        fields = ('id', 'code', 'name', 'description', 'reimbursed', 'exclusive_care_codes')


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
        fields = (
            'id', 'code_sn', 'first_name', 'name', 'address', 'zipcode', 'city', 'country', 'phone_number',
            'email_address', 'participation_statutaire', 'is_private', 'date_of_death')


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
    class Meta:
        model = MedicalPrescription
        fields = ('id', 'prescriptor', 'date', 'file')


class InvoiceItemSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if data['is_private'] != data['patient'].is_private:
            raise serializers.ValidationError("Only private Patients allowed in private Invoice Item.")

        return data

    class Meta:
        model = InvoiceItem
        fields = ('id', 'invoice_number', 'accident_id', 'accident_date', 'invoice_date', 'patient_invoice_date',
                  'invoice_send_date', 'invoice_sent', 'invoice_paid', 'medical_prescription', 'patient', 'prestations',
                  'is_private')


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
