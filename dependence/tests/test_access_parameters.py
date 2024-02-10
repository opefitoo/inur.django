from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.test import TestCase, RequestFactory

from dependence.admin import PatientParametersAdmin
from dependence.models import MonthlyParameters
from invoices.models import Patient, ClientPatientRelationship


class GetQuerySetTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.group = Group.objects.create(name='clients')
        self.user.groups.add(self.group)
        self.patient = Patient.objects.create(name='Test Patient')
        ClientPatientRelationship.objects.create(user=self.user, patient=self.patient)
        self.monthly_parameters = MonthlyParameters.objects.create(patient=self.patient, weight=80)
        self.admin = PatientParametersAdmin(MonthlyParameters, admin.site)

    def test_get_queryset_with_access(self):
        request = self.factory.get('/admin/dependence/monthlyparameters/')
        request.user = self.user
        queryset = self.admin.get_queryset(request)
        self.assertIn(self.monthly_parameters, queryset)

    def test_get_queryset_without_access(self):
        new_user = User.objects.create_user(username='newuser', password='12345')
        new_user.groups.add(self.group)
        request = self.factory.get('/admin')
        request.user = new_user
        queryset = self.admin.get_queryset(request)
        self.assertNotIn(self.monthly_parameters, queryset)
