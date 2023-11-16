import datetime
from decimal import Decimal

import requests

from invoices.models import InvoiceItem
from invoices.xero.utils import get_xero_token, ensure_contact_exists, attach_pdf_to_invoice


def create_xero_invoice(invoice_item: InvoiceItem, invoice_amount: Decimal, invoice_pdf_file=None):
    token = get_xero_token()

    # headers = {
    #     'Authorization': f'Bearer {token.access_token}',
    #     'Content-Type': 'application/json'
    # }
    # response = requests.get('https://api.xero.com/connections', headers=headers)
    # tenants = response.json()
    # print("tenants: ", tenants)

    if invoice_item.invoice_details.xero_tenant_id is None:
        raise Exception("No xero_tenant_id for invoice_details: ", invoice_item.invoice_details)

    # upper case first letter of first_name and capitalize all letters of name
    contact = ensure_contact_exists(token.access_token,
                                    invoice_item.invoice_details.xero_tenant_id,
                                    invoice_item.patient)

    invoice_data = {
        "Invoices": [
            {
                "Type": "ACCREC",
                "InvoiceNumber": "INV-NUNO-" + invoice_item.invoice_number,
                "Date": invoice_item.invoice_date.strftime("%Y-%m-%d"),
                # Due Date is 30 days from now
                "DueDate": (invoice_item.invoice_date + datetime.timedelta(days=20)).strftime("%Y-%m-%d"),
                "Contact": {
                    "ContactID": contact["ContactID"]  # Replace with a valid contact ID
                },
                "LineItems": [
                    {
                        "Description": "Soins infirmiers facture: %s" % invoice_item.invoice_number,
                        "Quantity": 1.0,
                        "UnitAmount":str(invoice_amount),
                        "AccountCode": "200"  # Replace with a valid account code
                    }
                ],
                # ... additional invoice details ...
            }
        ]
    }

    headers = {
        'Authorization': f'Bearer {token.access_token}',
        'Content-Type': 'application/json',
        'Xero-tenant-id': invoice_item.invoice_details.xero_tenant_id ,  # Replace with your Xero Tenant ID
        'Accept': 'application/json'
    }

    response = requests.post(
        'https://api.xero.com/api.xro/2.0/Invoices',
        json=invoice_data,
        headers=headers
    )

    if response.status_code == 200:
        xero_invoice_id = response.json().get('Invoices', [])[0]['InvoiceID']
        invoice_item.xero_invoice_url = 'https://go.xero.com/AccountsReceivable/View.aspx?InvoiceID=%s' % xero_invoice_id
        invoice_item.save()
    else:
        # Handle error (e.g., log the issue or throw an exception)
        response.raise_for_status()
        if invoice_item.xero_invoice_url:
            invoice_item.xero_invoice_url = None
            invoice_item.save()
    response = attach_pdf_to_invoice(token.access_token,
                                     invoice_item.invoice_details.xero_tenant_id,
                                     xero_invoice_id,
                                     invoice_pdf_file,
                                     invoice_item.invoice_number)
    if response.status_code == 200:
        return response.json().get('Status', [])
    else:
        # Handle error (e.g., log the issue or throw an exception)
        response.raise_for_status()



