import os

from django.core.cache import cache
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from invoices import settings


class GoogleContacts:
    SCOPES = ['https://www.googleapis.com/auth/contacts']

    def __init__(self, json_keyfile_path=None, email=None):
        self.credential_file = json_keyfile_path or settings.GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE2
        self.email = email
        self.creds = None
        self.load_credentials()
        self.service = build('people', 'v1', credentials=self.creds)

    def load_credentials(self):
        credentials = service_account.Credentials.from_service_account_file(
            self.credential_file, scopes=self.SCOPES)
        if self.email:
            delegated_credentials = credentials.with_subject(self.email)
        else:
            delegated_credentials = credentials.with_subject(os.environ.get('GOOGLE_EMAIL_CREDENTIALS', None))
        self.creds = delegated_credentials

    def get_contacts(self):
        # Try to get contacts from cache
        contacts = cache.get('google_contacts')
        if contacts is not None:
            return contacts

        # If contacts were not in cache, fetch them and store in cache
        contacts_service = self.service.people().connections()
        request = contacts_service.list(
            resourceName='people/me',
            pageSize=100,
            personFields='names,emailAddresses',
        )
        response = request.execute()
        if 'connections' in response:
            contacts = response['connections']
        else:
            raise Exception('No contacts found : %s' % response)

        # Cache the contacts for 1 hour (3600 seconds)
        cache.set('google_contacts', contacts, 3600)

        return contacts

    def contact_exists(self, first_name, family_name, sn_code):
        try:
            contacts = self.get_contacts()
            for person in contacts:
                names = person.get('names', [])
                user_defined_fields = person.get('userDefined', [])
                for name in names:
                    if name['givenName'] == first_name and name['familyName'] == family_name:
                        for field in user_defined_fields:
                            if field['key'] == 'sn_code' and field['value'] == sn_code:
                                return True
            return False
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False

    def add_contact(self, data):
        # Check if the contact already exists
        names = data.get('names', [])
        user_defined_fields = data.get('userDefined', [])
        if names and user_defined_fields:
            first_name = names[0]['givenName']
            family_name = names[0]['familyName']
            sn_code = next((field['value'] for field in user_defined_fields if field['key'] == 'sn_code'), None)
            if self.contact_exists(first_name, family_name, sn_code):
                print(f"Contact {first_name} {family_name} with SN Code {sn_code} already exists.")
                return None

        # If the contact does not exist, create it
        return self.service.people().createContact(body=data).execute()

    def add_or_update_contact(self, data):
        names = data.get('names', [])
        user_defined_fields = data.get('userDefined', [])
        if names and user_defined_fields:
            first_name = names[0]['givenName']
            family_name = names[0]['familyName']
            sn_code = next((field['value'] for field in user_defined_fields if field['key'] == 'sn_code'), None)

            # Check if the contact already exists
            if self.contact_exists(first_name, family_name, sn_code):
                # If the contact exists, update it
                print(f"Contact {first_name} {family_name} with SN Code {sn_code} already exists, updating it...")

                # We need to fetch all contacts and find the contact to be updated to get its resourceName
                results = self.service.people().connections().list(resourceName='people/me',
                                                                   personFields='names,userDefined,metadata').execute()
                connections = results.get('connections', [])
                for person in connections:
                    person_names = person.get('names', [])
                    person_user_defined_fields = person.get('userDefined', [])
                    for name in person_names:
                        if name['givenName'] == first_name and name['familyName'] == family_name:
                            for field in person_user_defined_fields:
                                if field['key'] == 'sn_code' and field['value'] == sn_code:
                                    # We found the existing contact, now let's update it
                                    existing_contact_resource_name = person['resourceName']
                                    existing_contact_etag = person['etag']  # get the etag

                                    # Include the etag in the data for update
                                    data['etag'] = existing_contact_etag

                                    update_mask = ",".join(
                                        [k for k in data.keys() if k != 'etag'])  # Exclude 'etag' from the update mask
                                    return self.service.people().updateContact(
                                        resourceName=existing_contact_resource_name,
                                        updatePersonFields=update_mask,
                                        body=data
                                    ).execute()
                print(f"Failed to find existing contact {first_name} {family_name} with SN Code {sn_code} for update.")
            else:
                # If the contact does not exist, create it
                print(f"Creating new contact {first_name} {family_name} with SN Code {sn_code}...")
                return self.service.people().createContact(body=data).execute()

    def get_or_create_contact_group(self, group_name):
        try:
            results = self.service.contactGroups().list().execute()
            groups = results.get('contactGroups', [])
            for group in groups:
                if group['name'] == group_name:
                    return group['resourceName']

            # Create a new group if it does not exist
            new_group = self.service.contactGroups().create(body={"contactGroup": {"name": group_name}}).execute()
            return new_group['resourceName']
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def add_contact_to_group(self, contact_id, group_id):
        try:
            self.service.contactGroups().members().modify(
                resourceName=group_id,
                body={'resourceNamesToAdd': [contact_id]}
            ).execute()
        except HttpError as error:
            print(f"An error occurred: {error}")
