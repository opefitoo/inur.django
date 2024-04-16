from json import dumps

from constance import config
from django.contrib.auth.models import User
from django.core.mail import send_mail
from httplib2 import Http

from helpers.employee import get_admin_emails
from invoices import settings
from invoices.enums.holidays import HolidayRequestWorkflowStatus


def notify_holiday_request_validation(obj, request):
    if obj.do_not_notify:
        url = "%s%s " % (config.ROOT_URL, obj.get_admin_url())
        to_emails = get_admin_emails()
        holiday_request_requester = [User.objects.get(id=obj.employee_id).email]
        if HolidayRequestWorkflowStatus.ACCEPTED != obj.request_status:
            send_email_notification(
                '[DO NOT NOTIFY HAS BEEN CHECKED] Your holiday request has been rejected by %s' % request.user,
                'please check request of %s here %s' % (holiday_request_requester, url),
                to_emails)
        else:
            send_email_notification(
                '[DO NOT NOTIFY HAS BEEN CHECKED] Your holiday request has been validated by %s' % request.user,
                'please check request of %s here %s' % (holiday_request_requester, url),
                to_emails)
        return True
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
        from_email=settings.EMAIL_HOST_USER,
        auth_user=settings.EMAIL_AUTH_USER,
        recipient_list=to_emails,
    )


def notify_user_that_new_alert_is_created(instance, url, employee_email):
    to_emails = [employee_email]
    send_email_notification('New alert has been created',
                            'New alert has been created, please check %s' % url,
                            to_emails)
def notify_user_that_holiday_request_is_created(instance, url, employee_email):
    to_emails = [employee_email]
    send_email_notification('Your holiday request has been created',
                            'Your holiday request has been created, please that you have to wait for validation and if you have any questions, please contact your manager. '
                            'In case of desiderata please take into consideration that it can be transformed into a holiday request if not possible. please check. %s' % url,
                            to_emails)
    # translate notification message into french
    message = "Votre demande de congé a été créée, veuillez noter que vous devez attendre la validation et si vous avez des questions, veuillez contacter votre manager. " \
              "En cas de désiderata, veuillez noter qu'il peut être transformé AUTOMATIQUEMENT en demande de congé si cela n'est pas possible veuillez vérifier. %s" % url

    send_email_notification("Votre demande de congé a été créée", message, to_emails)

def notify_system_via_google_webhook(message):
    url = config.GOOGLE_CHAT_WEBHOOK_FOR_SYSTEM_NOTIF_URL
    #  check if url looks like a url
    if not url.startswith("https://"):
        url = settings.GOOGLE_CHAT_WEBHOOK_URL
        if not url.startswith("https://"):
            print(f"Notifying system via google webhook failed, please check webhook url in settings.py : {message}")
            return
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
