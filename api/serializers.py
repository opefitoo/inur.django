from django.contrib.auth.models import User, Group
from rest_framework import serializers
from invoices.models import CareCode


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
        fields = ('code', 'name', 'description', 'gross_amount', 'reimbursed')
