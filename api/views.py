import json

from constance import config
from django.contrib.auth.models import User, Group
from django.http import HttpResponse
from django.utils.datetime_safe import datetime
from rest_framework import viewsets, filters, status, generics
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import UserSerializer, GroupSerializer, CareCodeSerializer, PatientSerializer, \
    PrestationSerializer, \
    InvoiceItemSerializer, JobPositionSerializer, TimesheetSerializer, \
    TimesheetTaskSerializer, PhysicianSerializer, MedicalPrescriptionSerializer, HospitalizationSerializer, \
    ValidityDateSerializer, InvoiceItemBatchSerializer, EventTypeSerializer, EventSerializer, \
    PatientAnamnesisSerializer, CarePlanMasterSerializer, BirthdayEventSerializer, GenericEmployeeEventSerializer, \
    EmployeeAvatarSerializer, EmployeeSerializer, EmployeeContractSerializer, FullCalendarEventSerializer, \
    FullCalendarEmployeeSerializer
from api.utils import get_settings
from dependence.models import PatientAnamnesis
from helpers import holidays, careplan
from helpers.employee import get_employee_id_by_abbreviation, \
    get_current_employee_contract_details_by_employee_abbreviation
from invoices import settings
from invoices.employee import JobPosition, Employee
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.events import EventType, Event
from invoices.holidays import HolidayRequest
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization, \
    ValidityDate, InvoiceItemBatch
from invoices.processors.birthdays import process_and_generate
from invoices.processors.events import delete_events_created_by_script
from invoices.processors.timesheets import get_door_events_for_employee
from invoices.timesheet import Timesheet, TimesheetTask


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class EmployeeAvatarSerializerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows employees who want to be published on internet to be viewed.
    """
    queryset = Employee.objects.filter(to_be_published_on_www=True).order_by("start_contract")
    serializer_class = EmployeeAvatarSerializer

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class CareCodeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows CareCodes to be viewed.
    """
    queryset = CareCode.objects.all()
    serializer_class = CareCodeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['code', 'name']


class PatientViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Patients to be viewed.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class PhysicianViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Physicians to be viewed.
    """
    queryset = Physician.objects.all()
    serializer_class = PhysicianSerializer


class PrestationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Prestations to be viewed.
    """
    queryset = Prestation.objects.all()
    serializer_class = PrestationSerializer


class InvoiceItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows InvoiceItems to be viewed.
    """
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer


class JobPositionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows JobPositions to be viewed.
    """
    queryset = JobPosition.objects.all()
    serializer_class = JobPositionSerializer


class BatchViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows JobPositions to be viewed.
    """
    queryset = InvoiceItemBatch.objects.all()
    serializer_class = InvoiceItemBatchSerializer


class TimesheetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Timesheets to be viewed.
    """
    queryset = Timesheet.objects.all()
    serializer_class = TimesheetSerializer


class TimesheetTaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows TimesheetTasks to be viewed.
    """
    queryset = TimesheetTask.objects.all()
    serializer_class = TimesheetTaskSerializer


class MedicalPrescriptionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows MedicalPrescriptions to be viewed.
    """
    queryset = MedicalPrescription.objects.all()
    serializer_class = MedicalPrescriptionSerializer


class HospitalizationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Hospitalizations to be viewed.
    """
    queryset = Hospitalization.objects.all()
    serializer_class = HospitalizationSerializer


class ValidityDateViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows ValidityDates to be viewed.
    """
    queryset = ValidityDate.objects.all()
    serializer_class = ValidityDateSerializer


class EventTypeViewSet(viewsets.ModelViewSet):
    queryset = EventType.objects.all()
    serializer_class = EventTypeSerializer


class PatientAnamnesisViewSet(viewsets.ModelViewSet):
    queryset = PatientAnamnesis.objects.all()
    serializer_class = PatientAnamnesisSerializer


class GenericEmployeeEventList(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = GenericEmployeeEventSerializer

    def post(self, request, *args, **kwargs):
        if request.data['employees']:
            emp_id = get_employee_id_by_abbreviation(request.data['employees']).id
            request.data['employees'] = emp_id
            employee_bis = None
            if request.data['notes'].startswith("+"):
                employee_bis = get_employee_id_by_abbreviation(request.data['notes'].split("+")[1])
        result = self.create(request, *args, **kwargs)
        if result.status_code == status.HTTP_201_CREATED:
            instance = Event.objects.get(pk=result.data.get('id'))
            if employee_bis:
                instance.notes = "En collaboration avec %s %s - Tél %s" % (employee_bis.user.last_name,
                                                                           employee_bis.user.first_name,
                                                                           employee_bis.phone_number)
            assert isinstance(instance, Event)
        return result

    def get(self, request, *args, **kwargs):
        employee = self.request.query_params.get('employee', None)
        year = self.request.query_params.get('year', None)
        if employee is not None:
            self.queryset = self.queryset.filter(employees__id=employee)
        if year is not None:
            self.queryset = self.queryset.filter(day__year=year)
        return self.list(request, *args, **kwargs)



class FullCalendarEventViewSet(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = FullCalendarEventSerializer

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        json_data = json.dumps(serializer.data)
        print(json_data)
        return HttpResponse(json_data, content_type='application/json')

    def get_queryset(self, *args, **kwargs):
        # parameters look like 'start': ['2023-02-05T00:00:00'], 'end': ['2023-02-12T00:00:00']
        # we need to convert them to python date
        start = datetime.strptime(self.request.query_params['start'], '%Y-%m-%dT%H:%M:%S').date()
        end = datetime.strptime(self.request.query_params['end'], '%Y-%m-%dT%H:%M:%S').date()
        queryset = Event.objects.filter(day__gte=start, day__lte=end)
        return queryset

    def patch(self, request, *args, **kwargs):
        event = Event.objects.get(pk=request.data['id'])
        # if request.data['start'] contains Z, it means it is a json date
        if request.data['start'].endswith('Z'):
            event.day = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
            event.time_start_event = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M:%S.%fZ').time()
        else:
            event.day = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M').date()
            event.time_start_event = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M').time()
        if request.data.get('employee_id', None):
            employee = Employee.objects.get(id=request.data['employee_id'])
            event.employees = employee
        if request.data['end'].endswith('Z'):
            event.time_end_event = datetime.strptime(request.data['end'], '%Y-%m-%dT%H:%M:%S.%fZ').time()
        else:
            event.time_end_event = datetime.strptime(request.data['end'], '%Y-%m-%dT%H:%M').time()
        event.save()
        return HttpResponse("OK")



class AvailableEmployeeList(generics.ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = FullCalendarEmployeeSerializer

    # for a specific day and time, return the list of available employees
    # parameters are day start_time end_time
    # employee must not be on holiday and must be assigned to another event at the same time
    # holiday HolidayRequestWorkflowStatus must be VALIDATED
    def get(self, request, *args, **kwargs):
        start = datetime.strptime(self.request.query_params['start'], '%Y-%m-%dT%H:%M:%S')
        if self.request.query_params['end']:
            end = datetime.strptime(self.request.query_params['end'], '%Y-%m-%dT%H:%M:%S')
        else:
            end = start
        day = start.date()
        start_time = start.time()
        end_time = end.time()
        # get the list of employees on holiday
        # get holidays with start date and end date include day
        holiday_list = HolidayRequest.objects.filter(start_date__lte=day, end_date__gte=day,
                                                     request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        # get the list of employees assigned to an event at the same time, must remove current event otherwise it will be
        # removed from the list
        event_list = Event.objects.filter(day=day, time_start_event__lte=end_time, time_end_event__gte=start_time).exclude(
            id=self.request.query_params['id'])
        # get the list of employees not on holiday and not assigned to an event at the same time
        # take only employees who still have a contract
        queryset = Employee.objects.exclude(id__in=holiday_list.values_list('employee', flat=True)).exclude(
                id__in=event_list.values_list('employees', flat=True)).exclude(end_contract__lt=day)
        serializer = self.get_serializer(queryset, many=True)
        json_data = json.dumps(serializer.data)
        return HttpResponse(json_data, content_type='application/json')


    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
class EventList(generics.ListCreateAPIView):
    queryset = Event.objects.all().order_by("day", "time_start_event")
    serializer_class = EventSerializer

    def get(self, request, *args, **kwargs):
        employee = self.request.query_params.get('employee', None)
        year = self.request.query_params.get('year', None)
        ordering = self.request.query_params.get('ordering', None)
        if employee is not None:
            self.queryset = self.queryset.filter(employees__id=employee)
        if year is not None:
            self.queryset = self.queryset.filter(day__year=year)
        if ordering is not None:
            self.queryset = self.queryset.order_by(ordering)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.data['employees']:
            emp_id = get_employee_id_by_abbreviation(request.data['employees']).id
            request.data['employees'] = emp_id
            employee_bis = None
            if request.data['notes'].startswith("+"):
                employee_bis = get_employee_id_by_abbreviation(request.data['notes'].split("+")[1])
        result = self.create(request, *args, **kwargs)
        if result.status_code == status.HTTP_201_CREATED:
            instance = Event.objects.get(pk=result.data.get('id'))
            if employee_bis:
                instance.notes = "En collaboration avec %s %s - Tél %s" % (employee_bis.user.last_name,
                                                                           employee_bis.user.first_name,
                                                                           employee_bis.phone_number)
            assert isinstance(instance, Event)
            # if instance.event_type_enum == EventTypeEnum.BIRTHDAY:
            #     return "Birthday created"
            # gmail_event = create_or_update_google_calendar(instance)
            # if gmail_event.get('id'):
            #     instance.calendar_id = gmail_event.get('id')
            #     instance.calendar_url = gmail_event.get('htmlLink')
            #     instance.save()
            # else:
            #     instance.delete()
            #     return JsonResponse(result.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return result


@api_view(['POST'])
def cleanup_event(request):
    if 'POST' != request.method:  # user posting data
        return
    deleted_events = delete_events_created_by_script(int(float(request.data.get('year'))),
                                                     int(float(request.data.get('month'))))
    event_serializer = EventSerializer(deleted_events, many=True)
    return Response(event_serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
def get_employee_details(request):
    if 'POST' != request.method:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    employee = get_employee_id_by_abbreviation(request.data.get('abbreviation'))
    if employee:
        return Response(EmployeeSerializer(employee).data, status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def get_employee_contract_details_by_abbreviation(request):
    if 'POST' != request.method:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    employee = get_current_employee_contract_details_by_employee_abbreviation(request.data.get('abbreviation'))
    if employee:
        return Response(EmployeeContractSerializer(employee).data, status=status.HTTP_200_OK)
    else:
        return Response(status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def whois_off(request):
    if 'POST' == request.method:  # user posting data
        reqs = holidays.whois_off(datetime.strptime(request.data["day_off"], "%Y-%m-%d"))
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['POST'])
def whois_available(request):
    if 'POST' == request.method:  # user posting data
        reqs = holidays.whois_available(datetime.strptime(request.data["working_day"], "%Y-%m-%d"))
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['POST'])
def which_shift(request):
    if 'POST' == request.method:  # user posting data
        reqs = holidays.which_shift(datetime.strptime(request.data["working_day"], "%Y-%m-%d"))
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_bank_holidays(request):
    if 'GET' == request.method:  # user posting data
        reqs = holidays.get_bank_holidays(request.GET.get("year"), request.GET.get("month"))
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['GET'])
def how_many_care_given(request):
    if 'GET' == request.method:
        reqs = Prestation.objects.all().count() + Event.objects.filter(state=3).count()
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['GET'])
def how_many_patients(request):
    if 'GET' == request.method:
        reqs = Patient.objects.all().count()
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['GET'])
def how_many_care_hours(request):
    if 'GET' == request.method:
        reqs = Event.objects.all().count() * 2
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_active_care_plans(request):
    if 'GET' == request.method:  # user posting data
        care_plans = careplan.get_active_care_plans()
        return Response(CarePlanMasterSerializer(care_plans, many=True).data, status=status.HTTP_200_OK)


class EventDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class EventProcessorView(APIView):

    def get(self, request, *args, **kw):
        """
        Calling api this way: http://localhost:8000/api/v1/process/45/
        """
        result = process_and_generate(int(kw['numdays']))
        items_serializer = BirthdayEventSerializer(result, many=True)
        items = items_serializer.data
        response = Response(items, status=status.HTTP_200_OK)
        return response

class YaleEventProcessorView(APIView):
    def get(self, request, *args, **kw):
         """
         Calling api this way: http://localhost:8000/api/v1/yale_events/
         """
         employees = Employee.objects.filter(end_contract__isnull=True)
         items = ""
         for employee in employees:
             result = get_door_events_for_employee(employee=employee)
             items += result
             break
         response = Response(items, status=status.HTTP_200_OK)
         return response


class SettingViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def setting(self, request, allow_settings):
        if request.method == 'GET':
            # list all setting items
            return Response(data=get_settings(allow_settings))
        else:
            # change all allow setting items in allow_settings
            for key in request.data:
                if key in allow_settings and key in getattr(settings, 'CONSTANCE_CONFIG', {}):
                    value = request.data[key]
                    setattr(config, key, '' if value is None else value)
            return Response(data=get_settings(allow_settings))

    # def create(self, request):
    #     """
    #     <p>update with POST:<code>{'Key': new_value}</code>
    #     """
    #     allow_settings = [key for key, options in getattr(settings, 'CONSTANCE_CONFIG', {}).items()]
    #     return self.setting(request, allow_settings)

    def list(self, request):
        """
        get all setting item
        """
        allow_settings = [key for key, options in getattr(settings, 'CONSTANCE_CONFIG', {}).items()]
        return self.setting(request, allow_settings)
