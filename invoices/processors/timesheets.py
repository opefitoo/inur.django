import pytz
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from invoices.employee import Employee, JobPosition
from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail
from invoices.yale.api import get_yale_house_activities
from invoices.yale.model import DoorEvent


def get_door_events(event_day=None):
    sheet_year = timezone.now().year
    sheet_month = timezone.now().month

    sheets = SimplifiedTimesheet.objects.filter(time_sheet_year=sheet_year, time_sheet_month=sheet_month)
    for sheet in sheets:
        # details = sheet.simplifiedtimesheetdetail_set()
        details = SimplifiedTimesheetDetail.objects.filter(simplified_timesheet_id=sheet.id,
                                                           start_date__day=event_day.day if event_day else timezone.now().day)
        for detail in details:
            print(detail)

    return sheets


def get_door_events_for_employee(employee):
    house_activities = get_yale_house_activities()
    for doorOperationActivity in house_activities:
        if hasattr(doorOperationActivity, "operated_by") \
                and doorOperationActivity.operated_by \
                and "Manual Lock" != doorOperationActivity.operated_by:
            # operated_by = Employee.objects.filter(user__first_name__contains=doorOperationActivity.operated_by)
            operated_by = Employee.objects.filter(
                Q(user__first_name__icontains=doorOperationActivity.operated_by.strip().split(" ")[-1]) | Q(
                    user__last_name__icontains=doorOperationActivity.operated_by.strip().split(" ")[-1])).exclude(abbreviation="XXX")
            if len(operated_by) > 1:
                raise Exception("Too many (%d) '%s'" % (len(operated_by), doorOperationActivity.operated_by))
            if len(operated_by) == 0:
                raise Exception("No user found '%s'" % doorOperationActivity.operated_by)
            door_event = DoorEvent.objects.get_or_create(employee=operated_by.first(),
                                                         activity_type=doorOperationActivity.activity_type,
                                                         activity_start_time=doorOperationActivity.activity_start_time.astimezone(
                                                             tz=pytz.UTC),
                                                         activity_end_time=doorOperationActivity.activity_end_time.astimezone(
                                                             tz=pytz.UTC),
                                                         action=doorOperationActivity.action,
                                                         created_by="get_door_events_for_employee")
        elif hasattr(doorOperationActivity, "operated_by") \
                and doorOperationActivity.operated_by \
                and "Manual Lock" == doorOperationActivity.operated_by:
            manual_lock_user, created = User.objects.get_or_create(first_name='Manual', last_name='Lock')
            job_position, create = JobPosition.objects.get_or_create(name='xxx_manual_lock_technical_occupation')
            manual_lock_employee, created = Employee.objects.get_or_create(user=manual_lock_user,
                                                                  start_contract=timezone.now(),
                                                                  occupation=job_position)
            door_event = DoorEvent.objects.get_or_create(employee=manual_lock_employee,
                                                         activity_type=doorOperationActivity.activity_type,
                                                         activity_start_time=doorOperationActivity.activity_start_time.astimezone(
                                                             tz=pytz.UTC),
                                                         activity_end_time=doorOperationActivity.activity_end_time.astimezone(
                                                             tz=pytz.UTC),
                                                         action=doorOperationActivity.action,
                                                         created_by="get_door_events_for_employee")


    # print(house_activities)
    return "sheets"
