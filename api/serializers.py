from django.contrib.auth.models import User, Group
from rest_framework import serializers
from django_countries.serializers import CountryFieldMixin
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription
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
        is_private = False
        if 'is_private' in data:
            is_private = data['is_private']
        is_code_sn_valid, message = Patient.is_code_sn_valid(is_private, data['code_sn'])
        if not is_code_sn_valid:
            raise serializers.ValidationError(message)

        return data

    class Meta:
        model = Patient
        fields = (
            'id', 'code_sn', 'first_name', 'name', 'address', 'zipcode', 'city', 'country', 'phone_number',
            'email_address', 'participation_statutaire', 'is_private')


class PhysicianSerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = Physician
        fields = (
            'id', 'provider_code', 'first_name', 'name', 'address', 'zipcode', 'city', 'country', 'phone_number',
            'fax_number', 'email_address')


class PrestationSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if 'at_home' in data and data['at_home'] and not Prestation.check_default_at_home_carecode_exists():
            raise serializers.ValidationError(Prestation.at_home_carecode_does_not_exist_msg())

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
