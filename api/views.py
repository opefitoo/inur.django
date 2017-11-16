from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from serializers import UserSerializer, GroupSerializer, CareCodeSerializer
from invoices.models import CareCode


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
