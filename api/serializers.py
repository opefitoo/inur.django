import datetime

from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import Promise
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from dependence.activity import LongTermMonthlyActivity, LongTermMonthlyActivityDetail
from dependence.careplan import CarePlanMaster, CarePlanDetail
from dependence.longtermcareitem import LongTermCareItem
from dependence.models import PatientAnamnesis, AssignedPhysician
from invoices.distancematrix import DistanceMatrix
from invoices.employee import JobPosition, Employee, EmployeeContractDetail, Shift, EmployeeShift
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.events import EventType, Event
from invoices.holidays import HolidayRequest
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization, \
    ValidityDate, InvoiceItemBatch, extract_birth_date_iso, SubContractor
from invoices.modelspackage import InvoicingDetails
from invoices.resources import Car, CarBooking
from invoices.timesheet import Timesheet, TimesheetTask, SimplifiedTimesheet


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')


class FullCalendarEmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Employee
        fields = ('id', 'abbreviation', 'user', 'color_cell', 'color_text')
        depth = 1


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ['id', 'name', 'start_time', 'end_time']


class EmployeeShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShift
        fields = ('id', 'employee', 'shift', 'date')


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = ['id', 'name', 'start_time', 'end_time']


class HolidayRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayRequest
        fields = ['id', 'start_date', 'end_date', 'request_status', 'employee', 'reason', 'hours_taken']


class SimplifiedTimesheetSerializer(serializers.ModelSerializer):
    holiday_requests = serializers.SerializerMethodField()
    employee_abbreviation = serializers.CharField(source='employee.abbreviation', read_only=True)

    class Meta:
        model = SimplifiedTimesheet
        fields = ['id', 'employee', 'employee_abbreviation', 'time_sheet_year', 'total_hours_sundays',
                  'time_sheet_month', 'hours_should_work', 'total_hours_public_holidays', 'holiday_requests']

    def get_holiday_requests(self, obj):
        holiday_requests = HolidayRequest.objects.filter(
            Q(employee=obj.employee.user),
            Q(request_status=HolidayRequestWorkflowStatus.ACCEPTED),
            Q(start_date__year=obj.time_sheet_year, start_date__month=obj.time_sheet_month) |
            Q(end_date__year=obj.time_sheet_year, end_date__month=obj.time_sheet_month)
        )
        return HolidayRequestSerializer(holiday_requests, many=True).data


class EmployeeAbbreviationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['abbreviation']


class EmployeeShiftSerializer(serializers.ModelSerializer):
    employee = EmployeeAbbreviationSerializer(read_only=True)

    class Meta:
        model = EmployeeShift
        fields = ['id', 'employee', 'shift', 'date']


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Employee
        fields = ('user', 'address', 'occupation', 'birth_date', 'birth_place', 'gender', 'address',
                  'virtual_career_anniversary_date')
        depth = 1


class EmployeeContractDetailSerializer(serializers.ModelSerializer):
    employee_link = EmployeeSerializer()

    class Meta:
        model = EmployeeContractDetail
        fields = ('start_date', 'number_of_hours', 'number_of_days_holidays', 'monthly_wage', 'contract_date',
                  'contract_signed_date', 'employee_trial_period_text', 'employee_special_conditions_text', 'index',
                  'career_rank', 'anniversary_career_rank', 'weekly_work_organization', 'employee_link')
        depth = 1


class DistanceMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = DistanceMatrix
        fields = ('patient_origin', 'patient_destination', 'distance_in_km', 'duration_in_mn')


class EmployeeContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeContractDetail
        fields = ('start_date', 'number_of_hours', 'number_of_days_holidays', 'monthly_wage', 'contract_date',
                  'contract_signed_date', 'employee_trial_period_text', 'employee_special_conditions_text', 'index',
                  'career_rank', 'anniversary_career_rank', 'weekly_work_organization')
        depth = 1


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
    # anamnesis_set = PatientAnamnesisSerializer(required=False)
    anamnesis_set = serializers.SerializerMethodField()
    birth_date = serializers.SerializerMethodField()
    full_address = serializers.CharField(required=False)

    def validate(self, data):
        instance_id = None
        if self.instance is not None:
            instance_id = self.instance.id

        messages = Patient.validate(instance_id, data)
        if messages:
            raise serializers.ValidationError(messages)

        return data

    def get_anamnesis_set(self, obj):
        anamnesis = PatientAnamnesis.objects.filter(patient=obj).order_by('-id').first()
        if anamnesis is not None:
            return PatientAnamnesisSerializer(anamnesis).data
        else:
            return None

    def get_birth_date(self, obj):
        # get extracted birth date from patient and serialize it as a date
        return extract_birth_date_iso(obj.code_sn)

    class Meta:
        model = Patient
        fields = '__all__'
        participation_statutaire = serializers.BooleanField(required=False, allow_null=True)
        is_private = serializers.BooleanField(required=False, allow_null=True)
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
        fields = ('id', 'prescriptor', 'patient', 'date', 'end_date', 'file_upload')


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
                  'is_private', 'invoice_details')


class InvoicingDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoicingDetails
        fields = ('id', 'provider_code', 'name')


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


class GenericEmployeeEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        day = serializers.DateField(format="%Y-%m-%d")
        # for DateTimeField
        time_start_event = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
        time_end_event = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
        fields = ('id', 'day', 'time_start_event', 'time_end_event', 'state', 'event_type_enum', 'notes',
                  'employees', 'created_by', "event_address", "calendar_url")
        validators = [
            UniqueTogetherValidator(
                queryset=Event.objects.all(),
                fields=['day', 'event_type_enum', 'time_start_event', 'time_end_event', 'employees']
            )
        ]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        order_by = ('day', 'time_start_event')
        model = Event
        day = serializers.DateField(format="%Y-%m-%d")
        # for DateTimeField
        time_start_event = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
        time_end_event = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
        fields = ('id', 'day', 'time_start_event', 'time_end_event', 'state', 'event_type_enum', 'notes', 'patient',
                  'employees', 'created_by', "event_address", "calendar_url")
        validators = [
            UniqueTogetherValidator(
                queryset=Event.objects.all(),
                fields=['day', 'event_type_enum', 'time_start_event', 'time_end_event', 'patient', 'employees']
            )
        ]


class FullCalendarPatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'first_name']


class SubContractorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubContractor
        fields = ['id', 'name', 'get_full_address', 'contractor_profession', 'created_on', 'updated_on',
                  'billing_retrocession', 'start_collaboration_date']


class FullCalendarEventSerializer(serializers.ModelSerializer):
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    textcolor = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    resourceId = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    event_report = serializers.SerializerMethodField()
    # mini_avatar is an image stored in s3 bucket
    minified_avatar = serializers.SerializerMethodField()
    minified_avatar_svg = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Convert all __proxy__ objects to strings
        for field in data:
            if isinstance(data[field], Promise):  # Check if the field is a lazy translation object
                data[field] = force_str(data[field])  # Convert to string
        return data

    def get_minified_avatar_svg(self, obj):
        cache_key = f"minified_avatar_svg_{obj.employees.id}"
        minified_avatar_svg = cache.get(cache_key)

        if minified_avatar_svg is None:
            minified_avatar_svg = obj.employees.minified_avatar_base64 if obj.employees and obj.employees.minified_avatar_base64 else None
            cache.set(cache_key, minified_avatar_svg, timeout=60 * 60)  # Cache for 1 hour

        return minified_avatar_svg

    def get_minified_avatar(self, obj):
        if obj.employees is not None and obj.employees.avatar is not None:
            # Use the EmployeeAvatarSerializer to get the avatar URL
            avatar_serializer = EmployeeAvatarSerializer(obj.employees)
            return avatar_serializer.data['avatar']
        return None

    def get_event_report(self, obj):
        if obj.event_report is None:
            return ""
        return obj.event_report

    def get_patient(self, obj):
        if obj.patient is not None:
            return obj.patient.id
        return None

    def get_start(self, obj):
        if obj.time_start_event is None:
            start_time = datetime.datetime.combine(obj.day, datetime.time(0, 0))
        else:
            start_time = datetime.datetime.combine(obj.day, obj.time_start_event)
        return timezone.datetime.combine(obj.day, start_time.time()).strftime("%Y-%m-%dT%H:%M:%S%z")

    def get_end(self, obj):
        if obj.time_end_event is None:
            end_time = datetime.datetime.combine(obj.day, obj.time_start_event)
            end_time += datetime.timedelta(hours=1)
        else:
            end_time = datetime.datetime.combine(obj.day, obj.time_end_event)
            return timezone.datetime.combine(obj.day, end_time.time()).strftime("%Y-%m-%dT%H:%M:%S%z")

    def get_title(self, obj):
        # call the __str__ method of the model
        return str(obj)

    def get_color(self, obj):
        # background color of the event is the same as the color of the event type employee
        if obj.employees is None:
            # default color is light-green
            return "#98FB98"
        return obj.employees.color_cell

    def get_textcolor(self, obj):
        # color of the event is the same as the color of the event type employee
        if obj.employees is None:
            # default color is gray
            return "#808080"
        return obj.employees.color_text

    # description is the notes of the event + event_report if it exists + patient name + patient first name + event state from STATES
    def get_description(self, obj):
        description = '<div id="mypopup">'
        if obj.employees is not None:
            description += '<h5>' "%s chez %s" % (
                obj.employees, str(obj.patient)) + '</h5>'  # Use the event title as the popup title
        else:
            description += '<h5>' "%s" % (str(obj.patient)) + '</h5>'

        if obj.notes is not None and obj.notes != "":
            description += '<p><b>Notes</b>:' + obj.notes + '</p>'

        if obj.event_report is not None and obj.event_report != "":
            description += '<p><b>Rapport</b>:' + obj.event_report + '</p>'

        if obj.state is not None and obj.state != "":
            if 0 <= obj.state <= len(Event.STATES):
                state_name = Event.STATES[obj.state - 1][1]
                if obj.state == 2:
                    description += '<p class="state-valid">' + state_name + '</p>'
                elif obj.state == 3:
                    description += '<p class="state-done">' + state_name + '</p>'
                else:
                    description += '<p class="state-cancelled">' + state_name + '</p>'
            else:
                description += '<p>' + str(obj.state) + '</p>'

        if obj.employees and obj.employees.minified_avatar_base64 is not None and obj.employees.minified_avatar_base64 != "":
            # Encode the ImageFieldFile data in base64
            description += '<img src="' + obj.employees.minified_avatar_base64 + '">'

        description += '</div>'
        return description + "(%s)" % obj.id

    # resource id is the id of the employee
    def get_resourceId(self, obj):
        if obj.employees is None:
            return None
        return obj.employees.id

    def get_notes(self, obj):
        if obj.notes is None or obj.notes == "":
            return ""
        return obj.notes

    def get_state(self, obj):
        # return state based on STATES
        if obj.state is None or obj.state == "":
            return ""
        if 0 <= obj.state <= len(Event.STATES):
            # return a json with id and name
            return {"state_id": obj.state, "state_name": Event.STATES[obj.state - 1][1]}
        else:
            return {"state_id": obj.state, "state_name": str(obj.state)}


class EmployeeAvatarSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Employee
        fields = ('user', 'avatar', 'minified_avatar', 'bio', 'occupation')
        depth = 1


class BirthdayEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        day = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
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


#
#     def create(self, validated_data):
#         long_term_care_item_code = validated_data.pop('long_term_care_item')
#         long_term_care_item_code_instance = LongTermCareItem.objects.get(code=long_term_care_item_code)
#         long_term_care_invoice_item = LongTermCareInvoiceItem.objects.create(long_term_care_item=long_term_care_item_code_instance,
#                                                                              assigned_employee=Employee.objects.get(id=1),
#                                                                              **validated_data)
#         return long_term_care_invoice_item
class LongTermItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LongTermCareItem
        fields = '__all__'


class LongTermMonthlyActivityDetailSerializer(serializers.ModelSerializer):
    activity = serializers.SlugRelatedField(slug_field='code', queryset=LongTermCareItem.objects.all())
    activity_date = serializers.DateField(format="%Y-%m-%d")

    class Meta:
        model = LongTermMonthlyActivityDetail
        fields = ['activity', 'quantity', 'activity_date']


class LongTermMonthlyActivitySerializer(serializers.ModelSerializer):
    activity_details = LongTermMonthlyActivityDetailSerializer(many=True)

    class Meta:
        model = LongTermMonthlyActivity
        fields = ['year', 'month', 'patient', 'activity_details']

    def create(self, validated_data):
        # validate that year month are the same as the activity details
        year = validated_data.get('year')
        month = validated_data.get('month')
        activity_details = validated_data.get('activity_details')
        for activity_detail in activity_details:
            activity_date = activity_detail.get('activity_date')
            if activity_date.year != year or activity_date.month != month:
                raise serializers.ValidationError(
                    "activity date %s does not match year %s and month %s" % (activity_date, year, month))
        activity_details_data = validated_data.pop('activity_details')
        long_term_monthly_activity = LongTermMonthlyActivity.objects.create(**validated_data)

        for activity_detail_data in activity_details_data:
            LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=long_term_monthly_activity,
                                                         **activity_detail_data)

        return long_term_monthly_activity

    def update(self, instance, validated_data):
        instance.year = validated_data.get('year', instance.year)
        instance.month = validated_data.get('month', instance.month)
        instance.patient = validated_data.get('patient', instance.patient)
        instance.save()

        activity_details_data = validated_data.pop('activity_details', [])

        # Delete existing activity details not in the updated data
        instance.activity_details.exclude(
            id__in=[item.get('id') for item in activity_details_data if item.get('id')]).delete()

        for activity_detail_data in activity_details_data:
            activity_detail_id = activity_detail_data.get('id', None)
            if activity_detail_id:
                # Update existing activity detail
                activity_detail = instance.activity_details.get(id=activity_detail_id)
                activity_detail.activity = activity_detail_data.get('activity', activity_detail.activity)
                activity_detail.quantity = activity_detail_data.get('quantity', activity_detail.quantity)
                activity_detail.activity_date = activity_detail_data.get('activity_date', activity_detail.activity_date)
                activity_detail.save()
            else:
                # Create new activity detail
                LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=instance,
                                                             **activity_detail_data)

        return instance


class CarBookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = CarBooking
        exclude = ['car_link']


class CarSerializer(serializers.ModelSerializer):
    can_lock = serializers.SerializerMethodField()
    can_unlock = serializers.SerializerMethodField()
    booked_for = CarBookingSerializer(read_only=True)
    #booked_for = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = ['id', 'name', 'vin_number', 'can_lock', 'can_unlock', 'booked_for']

    def get_can_lock(self, obj):
        # Assuming you have a method in your Car model that takes a user and returns a boolean
        return obj.can_user_lock(self.context['request'].user)

    def get_can_unlock(self, obj):
        # Assuming you have a method in your Car model that takes a user and returns a boolean
        return obj.can_user_unlock(self.context['request'].user)


