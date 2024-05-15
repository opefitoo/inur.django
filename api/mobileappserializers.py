from rest_framework import serializers

from dependence.models import TensionAndTemperatureParameters
from invoices.models import Patient
from invoices.visitmodels import EmployeeVisit


class MobilePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'
        #exclude = ['country']

class MobileTensionAndTemperatureParametersSerializer(serializers.ModelSerializer):
    class Meta:
        model = TensionAndTemperatureParameters
        # fields = '__all__'
        # exclude field 'country' from the serializer
        exclude = ['created_on', 'updated_on']


class MobileVisitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeVisit
        fields = '__all__'
        #exclude = ['country']
