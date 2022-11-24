from constance import config
from django.contrib.auth.models import User
from django.core.mail import send_mail

from invoices.enums.holidays import HolidayRequestWorkflowStatus


def notify_holiday_request_validation(obj, request):
    to_emails = [User.objects.get(id=obj.employee_id).email]
    url = "%s%s " % (config.ROOT_URL, obj.get_admin_url())
    if HolidayRequestWorkflowStatus.ACCEPTED != obj.request_status:
        send_email_notification('Your holiday request has been rejected by %s' % request.user,
                                'please check notes, request is:  %s.' % url,
                                to_emails)
    else:
        send_email_notification('Your holiday request has been validated by %s' % request.user,
                                'please check. %s' % url,
                                to_emails)


def send_email_notification(subject, message, to_emails):
    send_mail(
        subject,
        message,
        'noreply@opefitoo.org',
        to_emails,
    )
