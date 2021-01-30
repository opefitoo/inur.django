from django.contrib.auth.models import User
from django.core.mail import send_mail

from invoices.enums.holidays import HolidayRequestWorkflowStatus


def notify_holiday_request_validation(obj, request):
    to_emails = [User.objects.get(id=obj.employee_id).email]
    if HolidayRequestWorkflowStatus.ACCEPTED != obj.request_status:
        send_email_notification('Your holiday request has been rejected by %s' % request.user,
                                'please check. %s' % request.build_absolute_uri(),
                                to_emails)
    else:
        send_email_notification('Your holiday request has been validated by %s' % request.user,
                                'please check. %s' % request.build_absolute_uri(),
                                to_emails)


def send_email_notification(subject, message, to_emails):
    send_mail(
        subject,
        message,
        'noanswer@opefitoo.com',
        to_emails,
    )
