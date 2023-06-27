from io import BytesIO

from PyPDF2 import PdfMerger
from django.core.files.base import ContentFile
from django.db.models import Q
from django_rq import job
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate

from invoices import settings
from invoices.enums.generic import BatchTypeChoices
from invoices.invoiceitem_pdf import get_doc_elements
from invoices.notifications import notify_system_via_google_webhook
from invoices.prefac import generate_all_invoice_lines


@job
def process_post_save(instance):
    # calculate how much time it takes to process the batch
    from datetime import datetime
    start = datetime.now()
    _must_update = False

    if instance.force_update:
        _must_update = True
        instance.version += 1
        instance.force_update = False
    if _must_update:
        from invoices.models import InvoiceItem
        # Now update all InvoiceItems which have an invoice_date within this range
        if BatchTypeChoices.CNS_INF == instance.batch_type:
            batch_invoices = InvoiceItem.objects.filter(
                Q(invoice_date__gte=instance.start_date) & Q(invoice_date__lte=instance.end_date)).filter(
                invoice_sent=False)
            batch_invoices.update(batch=instance)
        batch_invoices = InvoiceItem.objects.filter(batch=instance)
        file_content = generate_all_invoice_lines(batch_invoices, sending_date=instance.send_date, batch_type=instance.batch_type)
        instance.prefac_file = ContentFile(file_content[0].encode('utf-8'), 'prefac.txt')

        # generate the pdf invoice file
        # Create a BytesIO buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm,
                                bottomMargin=1 * cm)
        elements, copies_of_medical_prescriptions = get_doc_elements(batch_invoices, med_p=True,
                                                                     with_verification_page=True)
        doc.build(elements)
        # Go to the beginning of the buffer
        buffer.seek(0)
        instance.generated_invoice_files = ContentFile(buffer.read(), 'invoice.pdf')

        merger = PdfMerger()
        for file in copies_of_medical_prescriptions:
            merger.append(file)
        pdf_buffer = BytesIO()
        merger.write(pdf_buffer)
        pdf_buffer.seek(0)
        instance.medical_prescriptions = ContentFile(pdf_buffer.read(), 'ordos.pdf')
        instance.save()
        end = datetime.now()
        notify_system_via_google_webhook("Batch {0} processed in {1} seconds".format(instance, (end - start).seconds))

#
# def sync_google_contacts(instance, **kwargs):
#     """
#     Connect to google contacts and sync user details (email, phone, name, avatar)
#     @param user_instance:
#     @return:
#     """
#     from googleapiclient.discovery import build
#     credentials = get_credentials()
#     service = build('people', 'v1', credentials=credentials)
#
#     # Attempt to find the contact by email
#     results = service.people().connections().list(
#         resourceName='people/me',
#         pageSize=1000,
#         personFields='emailAddresses').execute()
#     connections = results.get('connections', [])
#     for person in connections:
#         names = person.get('names', [])
#         if names:
#             name = names[0].get('displayName')
#         else:
#             name = 'No Name'
#         email_addresses = person.get('emailAddresses', [])
#         if email_addresses:
#             email = email_addresses[0].get('value')
#         else:
#             email = 'No Email'
#         print(name, email)
#         print(person)
#     # The employee was created. Create a new contact.
#     contact = {
#         'names': [{'givenName': instance.user.first_name, 'familyName': instance.user.last_name}],
#         'emailAddresses': [{'value': instance.user.email}],
#         # Add other fields as needed...
#     }
#
#     if kwargs.get('created', False):
#
#         service.people().createContact(body=contact).execute()
#     else:
#         # The employee was updated. Update the contact.
#         # Here, you'll need to know the 'resourceName' of the contact to update.
#         contact = service.people().get(resourceName="resourceName").execute()
#         contact['names'] = [{'givenName': instance.user.first_name, 'familyName': instance.user.last_name}]
#         contact['emailAddresses'] = [{'value': instance.user.email}]
#         # Add other fields as needed...
#         service.people().updateContact(resourceName="resourceName", body=contact).execute()
#
#
# def get_credentials():
#     import os
#     from google.oauth2 import service_account
#
#     # Load the credentials from an environment variable.
#     # credentials_json = os.getenv('GOOGLE_OAUTH_CREDENTIALS')
#
#     # Parse the JSON string into a Python dictionary.
#     # credentials_dict = json.loads(credentials_json)
#
#     # Convert the dictionary to a Credentials object.
#     # credentials = Credentials.from_authorized_user_info(credentials_dict)
#
#     # SCOPES = ['https://www.googleapis.com/auth/sqlservice.admin',
#     #          'https://www.googleapis.com/auth/people']
#
#     SCOPES = ["https://www.googleapis.com/auth/contacts",
#               "https://www.googleapis.com/auth/contacts.readonly"]
#     SCOPES___ = ['https://www.googleapis.com/auth/sqlservice.admin',
#                  'https://www.googleapis.com/auth/calendar']
#
#     _json_keyfile_path = settings.GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE2
#
#     # credentials_dict = json.loads(_json_keyfile_path)
#
#     # credentials = oauth2.credentials.Credentials(
#     #     credentials_dict["token"],
#     #     refresh_token=credentials_dict["refresh_token"],
#     #     token_uri=credentials_dict["token_uri"],
#     #     client_id=credentials_dict["client_id"],
#     #     client_secret=credentials_dict["client_secret"],
#     #     scopes=SCOPES)
#
#     delegated_credentials = service_account.Credentials.from_service_account_file(
#         _json_keyfile_path, scopes=SCOPES, subject=os.environ.get('GOOGLE_EMAIL_CREDENTIALS', None))
#     # delegated_credentials = credentials.with_subject(os.environ.get('GOOGLE_EMAIL_CREDENTIALS', None))
#     return delegated_credentials
