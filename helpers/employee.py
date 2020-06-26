from invoices.employee import Employee


def get_admin_emails():
    admin_emails = []
    for em in Employee.objects.filter(occupation__name='administratrice'):
        admin_emails.append(em.user.email)
    return admin_emails
