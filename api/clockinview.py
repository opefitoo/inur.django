from datetime import timezone

from django.http import JsonResponse
from django.utils.translation import gettext as _
from rest_framework.decorators import api_view
from api.clockinserializers import SimplifiedTimesheetClockInOutSerializer
from invoices.timesheet import SimplifiedTimesheetDetail


@api_view(['POST'])
def simplified_timesheet_clock_in_view(request):
    if request.method == 'POST':
        serializer = SimplifiedTimesheetClockInOutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({'status': 'success', 'message': _('Clock in successful')})
        return JsonResponse({'status': 'error', 'errors': serializer.errors})
    return JsonResponse({'status': 'error', 'errors': 'Invalid request'})

@api_view(['POST'])
def simplified_timesheet_clock_out_view(request):
    if request.method == 'POST':
        # Find the most recent SimplifiedTimesheetDetail for the current user
        timesheet_detail = SimplifiedTimesheetDetail.objects.filter(
            timesheet__employee=request.user,
            end_date__isnull=True
        ).order_by('-start_date').first()

        if timesheet_detail:
            # Set the end time to the current time
            timesheet_detail.end_date = timezone.now().time()
            timesheet_detail.save()
            return JsonResponse({'status': 'success', 'message': _('Clock out successful')})
        else:
            return JsonResponse({'status': 'error', 'errors': 'No active timesheet found'})
    return JsonResponse({'status': 'error', 'errors': 'Invalid request'})
