import requests
from django.conf import settings

from invoices.xeromodels import XeroToken


def get_xero_token():
    return XeroToken.refresh(
        settings.XERO_CLIENT_ID,
        settings.XERO_CLIENT_SECRET,
        settings.XERO_TOKEN_URL
    )


def get_xero_tenants():
    access_token = get_xero_token().access_token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get('https://api.xero.com/connections', headers=headers)
    return response.json()


def get_contact_by_identifier(access_token, xero_tenant_id, identifier):
    url = f'https://api.xero.com/api.xro/2.0/Contacts?where=Name=="{identifier}"'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    contacts = data.get('Contacts', [])
    return contacts[0] if contacts else None


def ensure_contact_exists(access_token, xero_tenant_id, contact_name):
    existing_contact = get_contact_by_identifier(access_token, xero_tenant_id, contact_name)

    if not existing_contact:
        # Define the new contact details
        new_contact_details = {
            'Name': contact_name,
            # Add other contact details as necessary
        }
        existing_contact = create_contact(access_token, xero_tenant_id, new_contact_details)

    return existing_contact


def create_contact(access_token, xero_tenant_id, contact_details):
    url = 'https://api.xero.com/api.xro/2.0/Contacts'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.post(url, headers=headers, json={'Contacts': [contact_details]})
    if response.status_code == 200:
        return response.json().get('Contacts', [])[0]
    else:
        # Handle error (e.g., log the issue or throw an exception)
        response.raise_for_status()


def attach_pdf_to_invoice(access_token, xero_tenant_id, invoice_id, pdf_content):
    url = f'https://api.xero.com/api.xro/2.0/Invoices/{invoice_id}/Attachments/sample.pdf'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Content-Type': 'application/pdf',
        'Accept': 'application/json'
    }

    response = requests.put(url, headers=headers, data=pdf_content, params={'IncludeOnline': 'true'})

    return response
