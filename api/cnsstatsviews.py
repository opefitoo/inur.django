from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from invoices.employee import EmployeeContractDetail


@api_view(['POST'])
def how_many_employees_with_specific_cct_sas_grade(request):
    if 'POST' != request.method:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    #list_all_active_contracts = employeestats.list_all_active_contracts()
    employees_count = EmployeeContractDetail.objects.filter(
        Q(career_rank__startswith=request.data.get('career_rank')) |
        Q(career_rank__isnull=True),  # Include this condition if needed
        Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
    ).count()
    return Response(employees_count, status=status.HTTP_200_OK)
