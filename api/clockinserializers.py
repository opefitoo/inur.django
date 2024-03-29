from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from invoices.employee import Employee
from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail


class SimplifiedTimesheetClockInOutSerializer(serializers.ModelSerializer):
    employee = PrimaryKeyRelatedField(queryset=Employee.objects.all())
    clock_in = serializers.DateTimeField(input_formats=['%Y-%m-%dT%H:%M:%SZ'], required=False)
    clock_out = serializers.DateTimeField(input_formats=['%Y-%m-%dT%H:%M:%SZ'], required=False)

    class Meta:
        model = SimplifiedTimesheet
        fields = ['employee', 'time_sheet_year', 'time_sheet_month', 'clock_in', 'clock_out']

    def validate(self, data):
        clock_in = data.get('clock_in')
        clock_out = data.get('clock_out')

        if clock_in and clock_out:
            raise serializers.ValidationError("Both clock_in and clock_out cannot be provided.")
        if not clock_in and not clock_out:
            raise serializers.ValidationError("Either clock_in or clock_out must be provided.")

        return data

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
            current_employee_contractual_hours = employee.get_current_contract().calculate_current_daily_hours()
            # timedetla cannot be later than 22:00
            # timedetla cannot be later than 22:00
            end_time = clock_in.time()
            # add a new SimplifiedTimesheetDetail with start time and end time
            SimplifiedTimesheetDetail.objects.create(simplified_timesheet=timesheet,
                                                     start_date=timezone.localtime(timezone.now()),
                                                     end_date=end_time)
        else:
            timesheet = SimplifiedTimesheet.objects.create(employee=employee, time_sheet_year=time_sheet_year,
                                                           time_sheet_month=time_sheet_month)
            current_employee_contractual_hours = employee.get_current_contract().calculate_current_daily_hours()
            # timedetla cannot be later than 22:00
            end_time = clock_in.time()
            SimplifiedTimesheetDetail.objects.create(simplified_timesheet=timesheet,
                                                     start_date=timezone.localtime(timezone.now()),
                                                     end_date=end_time)
        return timesheet
