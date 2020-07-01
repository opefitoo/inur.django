from django.contrib.auth.models import User, Group
from django.core.serializers import serialize
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import UserSerializer, GroupSerializer, CareCodeSerializer, PatientSerializer, \
    PrestationSerializer, \
    InvoiceItemSerializer, JobPositionSerializer, TimesheetSerializer, \
    TimesheetTaskSerializer, PhysicianSerializer, MedicalPrescriptionSerializer, HospitalizationSerializer, \
    ValidityDateSerializer, InvoiceItemBatchSerializer, EventTypeSerializer, EventSerializer
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Physician, MedicalPrescription, Hospitalization, \
    ValidityDate, InvoiceItemBatch
from invoices.processors.birthdays import process_and_generate
from invoices.timesheet import Timesheet, TimesheetTask
from invoices.employee import JobPosition
from invoices.events import EventType, Event


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


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer


class EventProcessorView(APIView):

    def get(self, request, *args, **kw):
        """
        Calling api this way:
        """
        result = process_and_generate(int(kw['numdays']))
        items_serializer = EventSerializer(result, many=True)
        items = items_serializer.data
        response = Response(items, status=status.HTTP_200_OK)
        return response
