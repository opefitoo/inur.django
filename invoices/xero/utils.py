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


def get_contact_by_identifier(access_token, xero_tenant_id, account_number=None):
    # search by AccountNumber
    url = 'https://api.xero.com/api.xro/2.0/Contacts?where=AccountNumber=="%s"' % account_number

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    contacts = data.get('Contacts', [])
    return contacts[0] if contacts else None


def ensure_contact_exists(access_token, xero_tenant_id, patient):
    _contact_name = patient.name.upper() + " " + patient.first_name.capitalize()
    # xero unique AccountNumber is 4011 + patient.id + patient.name.first_letter + patient.first_name.first_letter
    _xero_account_number = "4011" + str(patient.id) + patient.name[0].upper() + patient.first_name[0].upper()
    existing_contact = get_contact_by_identifier(access_token, xero_tenant_id, _xero_account_number)

    if not existing_contact:
        # Define the new contact details
        new_contact_details = {
            'Name': _contact_name,
            'AccountNumber':_xero_account_number,
            # Add other contact details as necessary
            'FirstName': patient.first_name.capitalize(),
            'LastName': patient.name.upper(),
            'EmailAddress': patient.email_address,
            'Addresses': [
                {
                    'AddressType': 'STREET',
                    'AddressLine1': patient.address,
                    'City': patient.city,
                    'PostalCode': patient.zipcode,
                    'Country': patient.country.code
                }
            ],
            'Phones': [
                {
                    'PhoneType': 'DEFAULT',
                    'PhoneNumber': patient.phone_number
                }
            ]

        }
        existing_contact = create_contact(access_token, xero_tenant_id, new_contact_details)
    else:
        # update contact details
        existing_contact['EmailAddress'] = patient.email_address
        existing_contact['Phones'][0]['PhoneNumber'] = patient.phone_number
        existing_contact['Addresses'][0]['AddressLine1'] = patient.address
        existing_contact['Addresses'][0]['City'] = patient.city
        existing_contact['Addresses'][0]['PostalCode'] = patient.zipcode
        existing_contact['Addresses'][0]['Country'] = patient.country.code

        existing_contact = update_contact(access_token, xero_tenant_id, existing_contact)


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

def update_contact(access_token, xero_tenant_id, contact_details):
    url = f'https://api.xero.com/api.xro/2.0/Contacts/{contact_details["ContactID"]}'
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


def attach_pdf_to_invoice(access_token, xero_tenant_id, invoice_id, pdf_content, invoice_number):
    url = f'https://api.xero.com/api.xro/2.0/Invoices/{invoice_id}/Attachments/{invoice_number}.pdf'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Content-Type': 'application/pdf',
        'Accept': 'application/json'
    }

    response = requests.put(url, headers=headers, data=pdf_content, params={'IncludeOnline': 'true'})

    return response

def get_account_transactions_between_dates(access_token, xero_tenant_id, account_code, start_date, end_date):
    _contact_name = "XXXX"
    xero_contact = get_contact_by_name(access_token, xero_tenant_id, _contact_name)
    if not xero_contact:
        raise Exception("Contact not found in Xero")
    # search all bank transactions for this contact
    url = 'https://api.xero.com/api.xro/2.0/BankTransactions?where=Contact.name=="%s"&page=1' % _contact_name
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Accept': 'application/json'
    }
    bank_transactions = []
    response = requests.get(url, headers=headers)
    data = response.json()
    bank_transactions += data.get('BankTransactions', [])
    for bank_transaction in bank_transactions:
        # replace the
        # set as reconciled false
        bank_transaction['IsReconciled'] = False
        # for  each line_item in bank_transaction['LineItems'] replace the account code 61111000 by 61112000
        for line_item in bank_transaction['LineItems']:
            if line_item['AccountCode'] == account_code:
                line_item['AccountCode'] = "61112000"
                line_item['TaxType'] = "NONE"
    # post the updated bank transactions
    url = 'https://api.xero.com/api.xro/2.0/BankTransactions/SummarizeErrors=false'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    response = requests.post(url, headers=headers, json={'BankTransactions': bank_transactions})
    if response.status_code == 200:
        return response.json().get('BankTransactions', [])
    else:
        # Handle error (e.g., log the issue or throw an exception)
        response.raise_for_status()


    return bank_transactions



def get_contact_by_name(access_token, xero_tenant_id, contact_name):

    # search by AccountNumber
    url = 'https://api.xero.com/api.xro/2.0/Contacts?where=Name=="%s"' % contact_name

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Xero-tenant-id': xero_tenant_id,
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    contacts = data.get('Contacts', [])
    return contacts[0] if contacts else None
