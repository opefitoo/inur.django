from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from serializers import UserSerializer, GroupSerializer, CareCodeSerializer, PatientSerializer, PrestationSerializer, \
    InvoiceItemSerializer, PrivateInvoiceItemSerializer, JobPositionSerializer, TimesheetSerializer, \
    TimesheetTaskSerializer
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, PrivateInvoiceItem
from invoices.timesheet import JobPosition, Timesheet, TimesheetTask


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows groups to be viewed.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class CareCodeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows CareCodes to be viewed.
    """
    queryset = CareCode.objects.all()
    serializer_class = CareCodeSerializer


class PatientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Patients to be viewed.
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class PrestationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Prestations to be viewed.
    """
    queryset = Prestation.objects.all()
    serializer_class = PrestationSerializer


class InvoiceItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows InvoiceItems to be viewed.
    """
    queryset = InvoiceItem.objects.all()
    serializer_class = InvoiceItemSerializer


class PrivateInvoiceItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows PrivateInvoiceItems to be viewed.
    """
    queryset = PrivateInvoiceItem.objects.all()
    serializer_class = PrivateInvoiceItemSerializer


class JobPositionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows JobPositions to be viewed.
    """
    queryset = JobPosition.objects.all()
    serializer_class = JobPositionSerializer


class TimesheetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Timesheets to be viewed.
    """
    queryset = Timesheet.objects.all()
    serializer_class = TimesheetSerializer


class TimesheetTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows TimesheetTasks to be viewed.
    """
    queryset = TimesheetTask.objects.all()
    serializer_class = TimesheetTaskSerializer
