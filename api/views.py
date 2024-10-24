import json
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from constance import config
from django.contrib.auth import authenticate
from django.contrib.auth.models import User, Group
from django.db.models import Count
from django.http import FileResponse
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, filters, status, generics
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from api.maps import create_distance_matrix
from api.serializers import UserSerializer, GroupSerializer, CareCodeSerializer, PatientSerializer, \
    PrestationSerializer, \
    InvoiceItemSerializer, JobPositionSerializer, TimesheetSerializer, \
    TimesheetTaskSerializer, PhysicianSerializer, MedicalPrescriptionSerializer, HospitalizationSerializer, \
    ValidityDateSerializer, InvoiceItemBatchSerializer, EventTypeSerializer, EventSerializer, \
    PatientAnamnesisSerializer, CarePlanMasterSerializer, BirthdayEventSerializer, GenericEmployeeEventSerializer, \
    EmployeeAvatarSerializer, EmployeeSerializer, EmployeeContractSerializer, FullCalendarEventSerializer, \
    FullCalendarEmployeeSerializer, FullCalendarPatientSerializer, \
    LongTermMonthlyActivitySerializer, DistanceMatrixSerializer, ShiftSerializer, EmployeeShiftSerializer, \
    SubContractorSerializer, SimplifiedTimesheetSerializer, CarSerializer, CarBookingSerializer
from api.utils import get_settings
from dependence.activity import LongTermMonthlyActivity
from dependence.careplan import CarePlanDetail, CarePlanMaster
from dependence.models import PatientAnamnesis
from helpers import holidays, careplan
from helpers.employee import get_employee_id_by_abbreviation, \
    get_current_employee_contract_details_by_employee_abbreviation
from helpers.patient import get_patient_by_id
from invoices import settings
from invoices.distancematrix import DistanceMatrix
from invoices.employee import JobPosition, Employee, EmployeeContractDetail, Shift, EmployeeShift
from invoices.employee import get_employee_by_abbreviation
from invoices.enums.event import EventTypeEnum
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.events import EventType, Event, create_or_update_google_calendar
from invoices.holidays import HolidayRequest
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization, \
    ValidityDate, InvoiceItemBatch, SubContractor
from invoices.processors.birthdays import process_and_generate
from invoices.processors.events import delete_events_created_by_script
from invoices.resources import Car, CarBooking
from invoices.timesheet import Timesheet, TimesheetTask, SimplifiedTimesheetDetail, SimplifiedTimesheet


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
    queryset = Employee.objects.filter(to_be_published_on_www=True).filter(end_contract=None).order_by("user__id")
    serializer_class = EmployeeAvatarSerializer


class ShyEmployeesViewSet(viewsets.ViewSet):
    """
    API endpoint that allows employees who want to be published on internet to be viewed.
    """

    def list(self, request):
        queryset = Employee.objects.exclude(to_be_published_on_www=True).filter(end_contract=None).order_by("user__id")
        queryset = queryset.values('occupation__name').annotate(total=Count('id')).order_by('occupation')
        occupation_counts = {item['occupation__name']: item['total'] for item in queryset}
        return Response(occupation_counts)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows employees who want to be published on internet to be viewed.
    """
    queryset = Employee.objects.all().order_by("start_contract")
    serializer_class = FullCalendarEmployeeSerializer


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


class DependantPatientViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Patients to be viewed.
    """
    queryset = Patient.objects.filter(is_under_dependence_insurance=True)
    serializer_class = PatientSerializer


class DistanceMatrixSerializerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows DistanceMatrix to be viewed.
    """
    queryset = DistanceMatrix.objects.all()
    serializer_class = DistanceMatrixSerializer


class DistanceAPIView(APIView):
    def get(self, request, origin, destination):
        # Assuming patient1 and patient2 are the addresses or identifiers
        # You need to retrieve these addresses from your patients database

        try:
            if origin == destination:
                return Response({'text': 'Distance to the same location is zero', 'distance': 0, 'duration': 0})
            distance_record = DistanceMatrix.objects.get(patient_origin_id=origin, patient_destination_id=destination)
            return Response({'text': str(distance_record), 'distance': distance_record.distance_in_km,
                             'duration': distance_record.duration_in_mn})
        except DistanceMatrix.DoesNotExist:
            return Response({'error': 'Distance not found'}, status=404)


class EmployeeContractDetailSerializerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows EmployeeContractDetail to be viewed.
    """
    queryset = EmployeeContractDetail.objects.all()
    serializer_class = EmployeeContractSerializer


class PhysicianViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Physicians to be viewed.
    """
    queryset = Physician.objects.all()
    serializer_class = PhysicianSerializer


class ShiftViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Shifts to be viewed.
    """
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer


class EmployeeShiftSerializerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows EmployeeShift to be viewed.
    """
    queryset = EmployeeShift.objects.all()
    serializer_class = EmployeeShiftSerializer


class EmployeeSerializerViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Employees to be viewed.
    """

    queryset = Employee.objects.filter(occupation__is_involved_in_health_care=True).order_by("start_contract")
    serializer_class = EmployeeSerializer


class PatientCarePlanView(generics.ListCreateAPIView):
    queryset = CarePlanMaster.objects.all()
    serializer_class = CarePlanMasterSerializer

    def get(self, request, patient_id):
        try:
            patient = Patient.objects.get(pk=patient_id)
            care_plans = CarePlanMaster.objects.filter(patient=patient)
            serializer = self.serializer_class(care_plans, many=True)
            # Do any additional processing or filtering on the careplan object here
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)


# class LongTermCareInvoiceFileView(generics.ListCreateAPIView):
#     queryset = LongTermCareInvoiceFile.objects.all()
#     serializer_class = LongTermCareInvoiceFileSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.serializer_class(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LongTermMonthlyActivityViewSet(viewsets.ModelViewSet):
    queryset = LongTermMonthlyActivity.objects.all()
    serializer_class = LongTermMonthlyActivitySerializer


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


def load_care_plans(request):
    patient_id = request.GET.get('patient')
    event_type = request.GET.get('event_type')
    if event_type != EventTypeEnum.ASS_DEP.value:
        return JsonResponse([], safe=False)
    care_plans = CarePlanDetail.objects.filter(care_plan_to_master__patient_id__exact=patient_id).order_by('time_start')
    # build a list of dictionaries with the care plan id and string representation
    care_plan_list = []
    for care_plan in care_plans:
        care_plan_list.append({'id': care_plan.id, 'name': str(care_plan)})
    return JsonResponse(care_plan_list, safe=False)


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


class NunoEventsService(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = FullCalendarEventSerializer

    def get(self, request, *args, **kwargs):
        # only today events for a specific employee, only abbreviation is provided
        abbreviation = request.query_params.get('abbreviation', None)
        username = request.query_params.get('username', None)
        if abbreviation is not None:
            employee = get_employee_by_abbreviation(abbreviation=abbreviation)
            self.queryset = self.queryset.filter(day=datetime.today().date(), employees=employee)
            return self.list(request, *args, **kwargs)
        if username is not None:
            employee = Employee.objects.get(user__username=username)
            # self.queryset = self.queryset.filter(day=datetime.today().date(), employees=employee)
            #
            self.queryset = self.queryset.filter(employees=employee)
            return self.list(request, *args, **kwargs)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, *args, **kwargs):
        try:
            event_data = json.loads(request.data.get('event'))
            event_id = event_data.get('id')
            if event_id is None:
                return JsonResponse({'error': 'No id provided'}, status=status.HTTP_400_BAD_REQUEST)

            event = Event.objects.get(pk=event_id)
            state_parameter = event_data['state']
            if state_parameter == 'cancel':
                event.state = 6
            elif state_parameter == 'done':
                event.state = 3
            elif state_parameter == 'not_done':
                event.state = 5
            event.event_report = event_data['event_report']

            # Check if there are files attached
            if 'files' in request.data:
                uploaded_files = request.data.getlist('files')
                for file in uploaded_files:
                    event.add_report_picture(file.name, file)

            event.save()
            return HttpResponse("OK")
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubContractorViewSet(viewsets.ModelViewSet):
    queryset = SubContractor.objects.all()
    serializer_class = SubContractorSerializer

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(occupation__is_subcontractor=True)
        return self.list(request, *args, **kwargs)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class FullCalendarEventViewSet(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = FullCalendarEventSerializer
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        # Convert __proxy__ objects to strings
        data = [{str(key): str(value) for key, value in item.items()} for item in serializer.data]
        json_data = json.dumps(data)
        return HttpResponse(json_data, content_type='application/json')

    def get_queryset(self, *args, **kwargs):
        start_param = self.request.query_params.get('start', datetime.today().date())
        end_param = self.request.query_params.get('end', datetime.today().date())
        start = datetime.strptime(start_param, '%Y-%m-%dT%H:%M:%S').date()
        end = datetime.strptime(end_param, '%Y-%m-%dT%H:%M:%S').date()
        queryset = Event.objects.filter(day__range=[start, end])
        return queryset

    def patch(self, request, *args, **kwargs):
        # if not superuser, can only validate events assigned to him
        if not request.user.is_superuser and not request.user.groups.filter(name="planning manager").exists():
            event = Event.objects.get(pk=request.data['id'])
            if event.employees and event.employees.user != request.user:
                return JsonResponse({'error': _('You are not allowed to validate this event')},
                                    status=status.HTTP_400_BAD_REQUEST)
        event = Event.objects.get(pk=request.data['id'])
        # if event state has changed but no report is provided, return an error
        if request.data.get('state', None) and event.state != int(request.data['state']) and not request.data.get(
                'eventReport', None):
            return JsonResponse({'error': _('Event report is required')}, status=status.HTTP_400_BAD_REQUEST)
        # cannot change state to done if event is in the future
        if request.data.get('state', None) and int(request.data['state']) == 3 and event.day > datetime.today().date():
            return JsonResponse({'error': _('Cannot change state to done for future event')},
                                status=status.HTTP_400_BAD_REQUEST)
        # if request.data['start'] contains Z, it means it is a json date
        event.state = request.data.get('state', event.state)
        if request.data['start'].endswith('Z'):
            event.day = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
            event.time_start_event = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M:%S.%fZ').time()
        else:
            event.day = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M:%S').date()
            event.time_start_event = datetime.strptime(request.data['start'], '%Y-%m-%dT%H:%M:%S').time()
        if request.data.get('employee_id', None):
            employee = Employee.objects.get(id=request.data['employee_id'])
            event.employees = employee
        if request.data['end'].endswith('Z'):
            event.time_end_event = datetime.strptime(request.data['end'], '%Y-%m-%dT%H:%M:%S.%fZ').time()
        elif request.data['end'].startswith('NaN'):
            event.time_end_event = None
        else:
            event.time_end_event = datetime.strptime(request.data['end'], '%Y-%m-%dT%H:%M:%S').time()
        if request.data.get('notes', None):
            event.notes = request.data['notes']
        if request.data.get('eventReport', None):
            event.event_report = request.data['eventReport']
        event.save()
        return HttpResponse("OK")

    def delete(self, request, *args, **kwargs):
        try:
            event_id = request.data.get('id')  # Get the event ID from the URL
            event = Event.objects.get(pk=event_id)
            # if event is not in the past but is already validated, you cannot delete it
            if event.state == 3:
                return JsonResponse(
                    {'error': _('Cannot delete validated event, event has report: %s') % event.event_report},
                    status=status.HTTP_400_BAD_REQUEST)
            # if event is the past you cannot delete it
            if event.day < datetime.today().date() and event.state not in (1, 2):
                return JsonResponse({'error': 'Cannot delete past event'}, status=status.HTTP_400_BAD_REQUEST)
            event.delete()
            return JsonResponse({'status': _('success')}, status=status.HTTP_204_NO_CONTENT)
        except Event.DoesNotExist:
            return JsonResponse({'error': _('Event not found')}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AvailablePatientList(generics.ListCreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = FullCalendarPatientSerializer

    def get(self, request, *args, **kwargs):
        event_type = self.request.query_params['event_type']
        if self.request.query_params['end']:
            end = datetime.strptime(self.request.query_params['end'], '%Y-%m-%dT%H:%M:%S')
        if EventTypeEnum.ASS_DEP == event_type:
            queryset = Patient.objects.filter(is_under_dependence_insurance=True,
                                              date_of_death__lte=end)
        else:
            queryset = Patient.objects.filter(date_of_death__lte=end)
        serializer = self.get_serializer(queryset, many=True)
        json_data = json.dumps(serializer.data)
        return HttpResponse(json_data, content_type='application/json')


class AvailableEventStateList(APIView):
    """
    API endpoint that returns available event states.
    """

    def get(self, request):
        states = Event.STATES
        states_list = [{"state_id": state[0], "state_name": state[1]} for state in states]
        return JsonResponse(states_list, safe=False)


class AvailableEmployeeList(generics.ListCreateAPIView):
    queryset = Employee.objects.all()
    serializer_class = FullCalendarEmployeeSerializer

    # for a specific day and time, return the list of available employees
    # parameters are day start_time end_time
    # employee must not be on holiday and must be assigned to another event at the same time
    # holiday HolidayRequestWorkflowStatus must be VALIDATED
    def get(self, request, *args, **kwargs):
        start = datetime.strptime(self.request.query_params['start'], '%Y-%m-%dT%H:%M:%S')
        # check if end is provided otherwise set it to start
        if self.request.query_params.get('end', None):
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
        event_list = Event.objects.filter(day=day, time_start_event__lte=end_time,
                                          time_end_event__gte=start_time).exclude(
            id=self.request.query_params['id']).exclude(employees=None).exclude(state__in=[4, 5, 6])
        # get the list of employees not on holiday and not assigned to an event at the same time
        # take only employees who still have a contract
        queryset = Employee.objects.exclude(user_id__in=holiday_list.values_list('employee', flat=True)).exclude(
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
                instance.notes = request.data['notes'] + "\n En collaboration avec %s %s - Tél %s" % (
                    employee_bis.user.last_name,
                    employee_bis.user.first_name,
                    employee_bis.phone_number)
            assert isinstance(instance, Event)
            # if instance.event_type_enum == EventTypeEnum.BIRTHDAY:
            #     return "Birthday created"
            if instance.event_type_enum != EventTypeEnum.SUB_CARE:
                gmail_event = create_or_update_google_calendar(instance)
                if gmail_event.get('id'):
                    instance.calendar_id = gmail_event.get('id')
                    instance.calendar_url = gmail_event.get('htmlLink')
                    instance.save()
                else:
                    instance.delete()
                    return JsonResponse(result.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
def calculate_distance_matrix(request):
    if 'POST' != request.method:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    if request.data.get('patient_ids'):
        patient_ids = request.data.get('patient_ids')
        active_patients = Patient.objects.filter(is_under_dependence_insurance=True).filter(
            date_of_death__isnull=True).filter(date_of_exit__isnull=True)
        # create a list that is intersection of active patients and patient_ids
        patient_ids = list(set(patient_ids).union(set(active_patients.values_list('id', flat=True))))
        # build a dict with patient as key and address as value
        patient_address_dict = {}
        for patient_id in patient_ids:
            patient = Patient.objects.get(pk=patient_id)
            patient_address_dict[patient] = patient.full_address
            # print("%s : %s" % (patient, patient.full_address))
        create_distance_matrix(patient_address_dict, config.DISTANCE_MATRIX_API_KEY)
        return Response(status=status.HTTP_200_OK)
    active_patients = Patient.objects.filter(is_under_dependence_insurance=True).filter(
        date_of_death__isnull=True).filter(date_of_exit__isnull=True)
    # build a dict with patient as key and address as value
    patient_address_dict = {}
    for active_patient in active_patients:
        patient_address_dict[active_patient] = active_patient.full_address
        # print("%s : %s" % (active_patient, active_patient.full_address))
    create_distance_matrix(patient_address_dict, config.DISTANCE_MATRIX_API_KEY)
    return Response(status=status.HTTP_200_OK)


import objgraph
from django.http import HttpResponse


def memory_profile(request):
    # Capture the 10 most common types in memory
    top_types = objgraph.most_common_types(limit=10, shortnames=False)

    # Optionally, capture and log a snapshot of the current state for later analysis
    objgraph.show_growth(limit=10)

    # Convert the data to a string to return as an HTTP response
    response_content = "\n".join(f"{typ}: {num}" for typ, num in top_types)
    return HttpResponse(response_content, content_type="text/plain")


def my_memory_debug_view(request):
    objects_of_type = objgraph.by_type('builtins.list')
    if not objects_of_type:
        return HttpResponse("No objects of type 'YourSuspiciousType' found.", content_type="text/plain")

    objgraph.show_chain(
        objgraph.find_backref_chain(
            random.choice(objects_of_type),
            objgraph.is_proper_module),
        filename='/tmp/chain.png')

    # Open the file in binary mode and return it as a response
    file_path = '/tmp/chain.png'
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            response = FileResponse(file, as_attachment=True, filename='chain.png')
            return response

    return HttpResponse("Chain image created at /tmp/chain.png", content_type="text/plain")


class SimplifiedTimesheetViewSet(viewsets.ModelViewSet):
    queryset = SimplifiedTimesheet.objects.all()
    serializer_class = SimplifiedTimesheetSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['employee__abbreviation', 'time_sheet_year', 'time_sheet_month']


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer


class EmployeeShiftViewSet(viewsets.ModelViewSet):
    queryset = EmployeeShift.objects.all()
    serializer_class = EmployeeShiftSerializer


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
def get_patient_details_by_id(request):
    if 'POST' != request.method:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    patient = get_patient_by_id(request.data.get('id'))
    if patient:
        return Response(PatientSerializer(patient).data, status=status.HTTP_200_OK)
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
        return (Response(reqs, status=status.HTTP_200_OK))


@api_view(['POST'])
@renderer_classes([JSONRenderer])
def whois_available_with_avatars_and_ids(request):
    if 'POST' == request.method:  # user posting data
        data = json.loads(request.body)
        reqs = holidays.whois_available_with_avatars_and_ids(datetime.strptime(data["working_day"], "%Y-%m-%d"))
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['POST'])
def which_shift(request):
    if 'POST' == request.method:  # user posting data
        reqs = holidays.which_shift(datetime.strptime(request.data["working_day"], "%Y-%m-%d"))
        return Response(reqs, status=status.HTTP_200_OK)


@api_view(['POST'])
def build_payroll_sheet(request):
    if 'POST' == request.method:
        # get employee abbreviation
        employee_abbreviation = request.data.get('employee_abbreviation')
        # get employee
        employee = Employee.objects.get(abbreviation=employee_abbreviation)
        # get date from request
        date = datetime.strptime(request.data.get('date'), "%Y-%m-%d")
        # get holiday request for this date and employee
        holiday_request = HolidayRequest.objects.filter(employee=employee.user, start_date__lte=date,
                                                        end_date__gte=date).first()
        if holiday_request:
            return Response(HolidayRequest.REASONS[holiday_request.reason - 1][1], status=status.HTTP_200_OK)
        # if there is a holiday request
        else:
            # SimplifiedTimesheet.objects.filter(employee=employee, date=date).get()
            # convert date to django compatible date for object filter
            # Set the timezone context to "America/Los_Angeles"
            if SimplifiedTimesheetDetail.objects.filter(simplified_timesheet__employee=employee,
                                                        start_date__year=date.year,
                                                        start_date__month=date.month,
                                                        start_date__day=date.day).exists():
                stdtl = SimplifiedTimesheetDetail.objects.filter(simplified_timesheet__employee=employee,
                                                                 start_date__year=date.year,
                                                                 start_date__month=date.month,
                                                                 start_date__day=date.day)
                string_to_return = ""
                for dtl in stdtl:
                    start_time = timezone.now().replace(
                        hour=dtl.start_date.astimezone(ZoneInfo("Europe/Luxembourg")).hour,
                        minute=dtl.start_date.minute)
                    end_time = timezone.now().replace(hour=dtl.end_date.hour,
                                                      minute=dtl.end_date.minute)
                    str_delta = ':'.join(str(dtl.time_delta()).split(':')[:2])
                    string_to_return += "De %s à %s (%s heures) " % (
                        start_time.strftime("%H:%M"), end_time.strftime("%H:%M"), str_delta)
                    return Response(string_to_return, status=status.HTTP_200_OK)
                # start_time = timezone.now().replace(hour=stdtl.get().start_date.astimezone(ZoneInfo("Europe/Luxembourg")).hour,
                #                                     minute=stdtl.get().start_date.minute)
                # end_time = timezone.now().replace(hour=stdtl.get().end_date.hour,
                #                                   minute=stdtl.get().end_date.minute)
                # # return only hours and minutes
                # # format hours and minutes
                # start_time_str = start_time.strftime("%H:%M")
                # end_time_str = end_time.strftime("%H:%M")
            else:
                return Response("OFF",
                                status=status.HTTP_200_OK)
            # format time delta which is of type datetime.timedelta to hours and minutes
            # return Response("De %s à %s (%s heures)" % (start_time_str, end_time_str, ':'.join(str(stdtl.get().time_delta()).split(':')[:2])),
            #                status=status.HTTP_200_OK)


@api_view(['GET'])
def get_bank_holidays(request):
    if 'GET' == request.method:  # user posting data
        reqs = holidays.get_bank_holidays(request.GET.get("year"), request.GET.get("month"))
        return Response(reqs, status=status.HTTP_200_OK)


@cache_page(60 * 60 * 24)  # Cache page for 24 hours
@api_view(['GET'])
def how_many_care_given(request):
    if 'GET' == request.method:
        reqs = Prestation.objects.all().count() + Event.objects.filter(state=3).count()
        return Response(reqs, status=status.HTTP_200_OK)


@cache_page(60 * 60 * 24)
@api_view(['GET'])
def how_many_patients(request):
    if 'GET' == request.method:
        reqs = Patient.objects.all().count()
        return Response(reqs, status=status.HTTP_200_OK)


@cache_page(60 * 60 * 24)
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


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            response = Response({'token': token.key, 'success': user.id})
            # Set the token in a cookie
            response.set_cookie('auth_token', token.key)
            return response
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_400_BAD_REQUEST)


class UnlockCarView(APIView):
    def post(self, request, *args, **kwargs):
        car = Car.objects.get(pk=kwargs['pk'])
        # first check if the user has a booking
        # if not, return a 403
        can_unlock = car.can_user_unlock(request.user)
        if not can_unlock:
            return HttpResponseForbidden({'status': 'error', 'message': 'User cannot unlock this car'})
        unlock_response = car.call_nodejs_api_to_unlock()
        if json.loads(unlock_response['message'])['success']:
            car.get_current_booking(request.user).unlock_car()
        return JsonResponse(unlock_response)


class LockCarView(APIView):
    def post(self, request, *args, **kwargs):
        car = Car.objects.get(pk=kwargs['pk'])
        # first check if the user has a booking
        # if not, return a 403
        can_lock = car.can_user_lock(request.user)
        if not can_lock:
            # return an error message
            return HttpResponseForbidden({'status': 'error', 'message': 'User cannot unlock this car'})
        lock_response = car.call_nodejs_api_to_lock()
        if json.loads(lock_response['message'])['success']:
            car.get_current_booking(request.user).lock_car()
        return JsonResponse(lock_response)


class CurrentUserCarBookingView(generics.ListAPIView):
    serializer_class = CarBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        current_time = timezone.now()
        return CarBooking.objects.filter(user=self.request.user, start_time__lte=current_time,
                                         end_time__gte=current_time)


class CarBookingListView(APIView):
    def get(self, request):
        car_bookings = CarBooking.objects.all()
        serialized_data = [booking.to_dict() for booking in car_bookings]
        return Response(serialized_data)


class CarViewSet(viewsets.ModelViewSet):
    queryset = Car.objects.filter(is_connected_to_bluelink=True)
    serializer_class = CarSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())  # Get the queryset of cars connected to bluelink
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@cache_page(60)
def car_location(request, car_id):
    try:
        car = Car.objects.get(pk=car_id)
        location = car.bluelink_location  # Assuming 'location' is a field in the Car model
        if location.get('success', None):
            return JsonResponse({'location': location})
        else:
            return JsonResponse({'error': 'Failed to get location'}, status=500)
    except Car.DoesNotExist:
        return JsonResponse({'error': 'Car not found'}, status=404)


def is_car_locked(request, car_id):
    try:
        car = Car.objects.get(pk=car_id)
        locked = car.locked  # Assuming 'locked' is a field in the Car model
        return JsonResponse({'locked': locked})
    except Car.DoesNotExist:
        return JsonResponse({'error': 'Car not found'}, status=404)


def can_user_lock_car(request, car_id):
    try:
        user = User.objects.get(pk=request.user.id)
        car = Car.objects.get(pk=car_id)
        # Check if the user is allowed to lock the car
        return JsonResponse({'can_lock': car.can_user_lock(user=user)})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Car.DoesNotExist:
        return JsonResponse({'error': 'Car not found'}, status=404)
