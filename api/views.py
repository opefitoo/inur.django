from constance import config
from django.contrib.auth.models import User, Group
from django.core.serializers import serialize
from django.http import JsonResponse
from rest_framework import viewsets, filters, status, generics
from rest_framework.decorators import action, api_view
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import UserSerializer, GroupSerializer, CareCodeSerializer, PatientSerializer, \
    PrestationSerializer, \
    InvoiceItemSerializer, JobPositionSerializer, TimesheetSerializer, \
    TimesheetTaskSerializer, PhysicianSerializer, MedicalPrescriptionSerializer, HospitalizationSerializer, \
    ValidityDateSerializer, InvoiceItemBatchSerializer, EventTypeSerializer, EventSerializer
from api.utils import get_settings
from helpers.employee import get_pks_all_active_employees, get_employee_id_by_abbreviation
from invoices import settings
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization, \
    ValidityDate, InvoiceItemBatch
from invoices.processors.birthdays import process_and_generate
from invoices.timesheet import Timesheet, TimesheetTask
from invoices.employee import JobPosition
from invoices.events import EventType, Event, create_or_update_google_calendar


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


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


class EventList(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def post(self, request, *args, **kwargs):
        if request.data['employees']:
            emp_id = get_employee_id_by_abbreviation(request.data['employees'])
            request.data['employees'] = emp_id
        result = self.create(request, *args, **kwargs)
        if result.status_code == status.HTTP_201_CREATED:
            instance = Event.objects.get(pk=result.data.get('id'))
            assert isinstance(instance, Event)
            gmail_event = create_or_update_google_calendar(instance)
            if gmail_event.get('id'):
                instance.calendar_id = gmail_event.get('id')
                instance.calendar_url = gmail_event.get('htmlLink')
                instance.save()
            else:
                instance.delete()
                return JsonResponse(result.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return result


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
        items_serializer = EventSerializer(result, many=True)
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
