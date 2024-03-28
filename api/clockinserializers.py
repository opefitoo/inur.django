from datetime import time

from rest_framework import serializers

from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail


class SimplifiedTimesheetClockInOutSerializer(serializers.ModelSerializer):
    clock_in = serializers.DateTimeField(input_formats=['%Y-%m-%dT%H:%M:%S.%fZ'], required=True)
    clock_out = serializers.DateTimeField(input_formats=['%Y-%m-%dT%H:%M:%S.%fZ'], required=False)

    class Meta:
        model = SimplifiedTimesheet
        fields = ['employee', 'time_sheet_year', 'time_sheet_month', 'clock_in', 'clock_out']

    def create(self, validated_data):
        employee = validated_data.get('employee')
        time_sheet_year = validated_data.get('time_sheet_year')
        time_sheet_month = validated_data.get('time_sheet_month')
        clock_in = validated_data.get('clock_in')
        clock_out = validated_data.get('clock_out')
        timesheet = SimplifiedTimesheet.objects.filter(employee=employee, time_sheet_year=time_sheet_year,
                                                       time_sheet_month=time_sheet_month).first()
        if timesheet:
            # check first if there is a detail with the same day
            SimplifiedTimesheetDetail.objects.filter(timesheet=timesheet, start_date__day=clock_in.day).delete()
            # end_time will be just time + 1 hour ( I need just the time )
            current_employee_contractual_hours = employee.get_current_contract().calculate_current_daily_hours()
            end_time = time(clock_in.hour + current_employee_contractual_hours, clock_in.minute, clock_in.second)
            # add a new SimplifiedTimesheetDetail with start time and end time
            SimplifiedTimesheetDetail.objects.create(timesheet=timesheet, start_date=clock_in, end_date=end_time)
        return timesheet
