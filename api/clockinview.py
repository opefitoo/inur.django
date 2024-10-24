
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view

from api.clockinserializers import SimplifiedTimesheetClockInOutSerializer
from invoices.employee import Employee
from invoices.timesheet import SimplifiedTimesheetDetail


@api_view(['POST'])
def simplified_timesheet_clock_in_view(request):
    if request.method == 'POST':
        serializer = SimplifiedTimesheetClockInOutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'status': 'success', 'message': _('Clock in successful')},
                                status=status.HTTP_201_CREATED)
        return JsonResponse({'status': 'error', 'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
    return JsonResponse({'status': 'error', 'errors': 'Invalid request'},
                        status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def simplified_timesheet_clock_out_view(request):
    if request.method == 'POST':
        serializer = SimplifiedTimesheetClockInOutSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'status': 'error', 'errors': serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
        # Find the most recent SimplifiedTimesheetDetail for the current user
            timesheet_detail = SimplifiedTimesheetDetail.objects.filter(
                simplified_timesheet__employee=Employee.objects.get(id=serializer.data.get('employee')),
                start_date__date=timezone.localtime(timezone.now()).date()
            ).order_by('-start_date').first()

            if timesheet_detail:
                # Set the end time to the current time
                timesheet_detail.end_date = timezone.localtime(timezone.now()).time()
                timesheet_detail.save()
                return JsonResponse({'status': 'success', 'message': _('Clock out successful')})
            else:
                return JsonResponse({'status': 'error', 'errors': 'No active timesheet found'})
        return JsonResponse({'status': 'error', 'errors': 'Invalid request'})
