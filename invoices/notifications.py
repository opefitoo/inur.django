import static
from django.core.mail import mail_admins, send_mail

from invoices.timesheet import Employee


def notify_holiday_request_validation(instance, request):
    url = instance.get_admin_url()
    print(url)
    to_emails = []
    for em in Employee.objects.filter(occupation__name='administratrice'):
        to_emails.append(em.user.email)
    send_email_notification_to_admins('You holiday request has been validated by %s' % instance.employee.user,
                                      'please check. %s' % request.get_aboslute_url(),
                                      to_emails)


def send_email_notification_to_admins(subject, message, to_emails):
    send_mail(
        subject,
        message,
        'nomail@benammar.com',
        to_emails,
    )
