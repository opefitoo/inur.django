from django.contrib.auth.models import User, Group
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from dependence.careplan import CarePlanMaster, CarePlanDetail
from dependence.models import PatientAnamnesis, AssignedPhysician
from invoices.employee import JobPosition
from invoices.events import EventType, Event
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization, \
    ValidityDate, InvoiceItemBatch
from invoices.timesheet import Timesheet, TimesheetTask


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
            'id', 'code', 'name', 'description', 'reimbursed', 'current_gross_amount', 'exclusive_care_codes',
            'validity_dates')


class PhysicianSerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = Physician
        fields = '__all__'


class PatientAnamnesisSerializer(CountryFieldMixin, serializers.ModelSerializer):
    physicians_set = PhysicianSerializer(many=True)

    class Meta:
        model = PatientAnamnesis
        fields = '__all__'


class AssignedPhysician(serializers.ModelSerializer):
    class Meta:
        model = AssignedPhysician
        fields = ('assigned_physician',)


class PatientSerializer(CountryFieldMixin, serializers.ModelSerializer):
    anamnesis_set = PatientAnamnesisSerializer(required=False)
    full_address = serializers.CharField(required=False)

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
        fields = '__all__'
        participation_statutaire = serializers.NullBooleanField(required=False)
        is_private = serializers.NullBooleanField(required=False)
        depth = 1


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


class EventTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventType
        fields = ('id', 'name')


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        day = serializers.DateField(format="%Y-%m-%d")
        # for DateTimeField
        time_start_event = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
        time_end_event = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
        fields = ('id', 'day', 'time_start_event', 'time_end_event', 'state', 'event_type_enum', 'notes', 'patient',
                  'employees', 'created_by')
        validators = [
            UniqueTogetherValidator(
                queryset=Event.objects.all(),
                fields=['day', 'event_type_enum', 'time_start_event', 'time_end_event', 'patient', 'employees']
            )
        ]


class BirthdayEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        day = serializers.DateField(format="%Y-%m-%d")
        fields = ('id', 'day', 'notes', 'patient', 'created_by')


class PatientSerializerForCarePlan(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name']


class CarePlanDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarePlanDetail
        fields = '__all__'


class CarePlanMasterSerializer(serializers.ModelSerializer):
    care_plan_detail_to_master = CarePlanDetailSerializer(many=True)
    patient = PatientSerializerForCarePlan()

    class Meta:
        model = CarePlanMaster
        fields = ['patient', 'plan_number', 'plan_start_date', 'care_plan_detail_to_master']
