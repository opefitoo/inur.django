from django.contrib.auth.models import User, Group
from rest_framework import serializers
from invoices.models import CareCode, Patient


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
        fields = ('id', 'code', 'name', 'description', 'gross_amount', 'reimbursed')


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ('id', 'code_sn', 'first_name', 'name', 'address', 'zipcode', 'city', 'phone_number', 'email_address',
                  'participation_statutaire', 'private_patient')
