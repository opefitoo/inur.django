from django.db import transaction


@transaction.atomic
def duplicate_for_next_month(self, request, queryset):
    # get all activities for this patient for this month
    for activity in queryset:
        activity.duplicate_for_next_month()
        activity.save()


from django.http import HttpResponse
import csv
from django.db.models import Sum
import calendar


def export_selected_to_csv(modeladmin, request, queryset):
    # French days of the week
    days_of_week_fr = ['Sam', 'Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven']

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="LongTermMonthlyActivity.csv"'
    writer = csv.writer(response)

    # We pick an arbitrary year and month (2024 and April) that starts on a Monday for convenience
    month = [(i, calendar.day_name[(i - 1) % 7]) for i in range(1, 32)]
    month_fr = [(i, days_of_week_fr[(i - 1) % 7]) for i, _ in month]

    for activity in queryset:
        writer.writerow(
            ['Patient: %s' % activity.patient, 'Activity Code', 'Short Description'] + [f"{i} ({day})" for i, day in
                                                                                        month_fr])
        unique_activities = activity.activity_details.values('activity__code', 'activity__description').annotate(
            total=Sum('quantity'))
        _counter = 0
        for unique_activity in unique_activities:
            _counter += 1
            row = [_counter, unique_activity['activity__code'],
                   unique_activity['activity__description']] + [''] * 31

            details = activity.activity_details.filter(activity__code=unique_activity['activity__code']).values(
                'activity_date').annotate(quantity=Sum('quantity'))
            for detail in details:
                row[detail['activity_date'].day - 1 + 3] = detail[
                    'quantity']  # +3 to account for the first three columns
            writer.writerow(row)

    return response


export_selected_to_csv.short_description = "Export selected to CSV"
