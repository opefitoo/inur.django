from json import dumps

from constance import config, settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from httplib2 import Http

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

def notify_system_via_google_webhook(message):
    url = settings.GOOGLE_CHAT_WEBHOOK_FOR_SYSTEM_NOTIF_URL
    bot_message = {
        'text': message}
    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}
    http_obj = Http()
    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=dumps(bot_message),
    )
    return response
