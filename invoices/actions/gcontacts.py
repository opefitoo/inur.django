import os

from django.core.cache import cache
from django_rq import job
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from invoices import settings


class GoogleContacts:
    SCOPES = ['https://www.googleapis.com/auth/contacts']

    def __init__(self, json_keyfile_path=None, email=None):
        self.credential_file = json_keyfile_path or settings.GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE2
        if not self.credential_file:
            raise Exception("Google Drive Storage JSON Key File not found")
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
            personFields='names,emailAddresses,userDefined',
        )
        response = request.execute()
        if 'connections' in response:
            contacts = response['connections']
        else:
            raise Exception('No contacts found : %s' % response)

        # Cache the contacts for 1 hour (3600 seconds)
        cache.set('google_contacts', contacts, 3600)

        return contacts

    def delete_contact(self, resource_name):
        try:
            deletion_result = self.service.people().deleteContact(resourceName=resource_name).execute()
            print(f"Contact {resource_name} deleted: {deletion_result} from {self.email}")
            return deletion_result
        except Exception as e:
            print(f"Failed to delete contact: {e}")
            return None

    def delete_all_contacts(self):
        contacts = self.get_contacts()
        for person in contacts:
            print(f"Deleting contact {person['resourceName']}...")
            self.delete_contact(person['resourceName'])

    def batch_delete_contacts(self, contacts):
        if len(contacts) > 0:
            # split contacts into batches of 500
            contacts_batches = [contacts[i:i + 500] for i in range(0, len(contacts), 500)]
            for batch in contacts_batches:
                print(f"Deleting {len(batch)} contacts...")
                batch_result = self.service.people().batchDeleteContacts(
                    body={"resourceNames": batch}
                ).execute()
                print(f"Batch delete result: {batch_result}")
        else:
            print("No contacts to delete.")

    def count_contacts_in_group(self, group_id):
        try:
            results = self.service.contactGroups().get(
                resourceName=group_id
            ).execute()
            return results.get('memberCount', 0)
        except HttpError as error:
            print(f"An error occurred: {error}")
            return 0

    def delete_all_contacts_in_group(self, group_name):
        group_id = self.get_group_id_by_name(group_name)
        if group_id:
            contacts = self.get_contacts_in_group(group_id)
            print(f"Deleting {len(contacts)} contacts in group {group_name}...")
            self.batch_delete_contacts(contacts)
        else:
            print(f"Group {group_name} not found.")

    def get_contacts_in_group(self, group_id):
        number_of_contacts = self.count_contacts_in_group(group_id)
        if number_of_contacts:
            print(f"Fetching {number_of_contacts} contacts in group {group_id}...")
            # loop until all contacts are fetched
            contacts = []
            results = self.service.contactGroups().batchGet(resourceNames=group_id,
                                                            maxMembers=number_of_contacts).execute()
            if 'memberResourceNames' in results['responses'][0]['contactGroup']:
                contacts.extend(results['responses'][0]['contactGroup']['memberResourceNames'])
            if len(contacts) < number_of_contacts:
                next_page_token = results['responses'][0].get('nextPageToken', None)
                while next_page_token:
                    results = self.service.contactGroups().batchGet(resourceNames=group_id,
                                                                    maxMembers=number_of_contacts,
                                                                    pageToken=next_page_token).execute()
                    if 'memberResourceNames' in results['responses'][0]['contactGroup']:
                        contacts.extend(results['responses'][0]['contactGroup']['memberResourceNames'])
                    next_page_token = results['responses'][0].get('nextPageToken', None)
            return contacts
        else:
            print(f"Group {group_id} not found.")
            return []

    def get_group_id_by_name(self, group_name):
        try:
            results = self.service.contactGroups().list().execute()
            groups = results.get('contactGroups', [])
            for group in groups:
                if group['name'] == group_name:
                    return group['resourceName']
            return None
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

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

    def find_contact_by_details(self, first_name, family_name, sn_code=None):
        ppl = self.service.people().searchContacts(query=f"{first_name} {family_name}",
                                                   readMask='names,userDefined').execute()
        if not ppl:
            # call it again with a different query
            ppl = self.service.people().searchContacts(query=f"{family_name} {first_name}",
                                                       readMask='names,userDefined').execute()
        for person in ppl.get('results', []):
            names = person['person'].get('names', [])
            user_defined_fields = person['person'].get('userDefined', [])
            for name in names:
                if name['givenName'] == first_name and name['familyName'] == family_name:
                    if sn_code:
                        for field in user_defined_fields:
                            if field['key'] == 'sn_code' and field['value'] == sn_code:
                                return person['person']
                    else:
                        return person['person']
        return None

    def add_contact(self, data):
        # Check if the contact already exists
        names = data.get('names', [])
        user_defined_fields = data.get('userDefined', [])
        if names and user_defined_fields:
            first_name = names[0]['givenName']
            family_name = names[0]['familyName']
            sn_code = next((field['value'] for field in user_defined_fields if field['key'] == 'sn_code'), None)
            existing_contact = self.find_contact_by_details(first_name, family_name, sn_code=sn_code)
            if existing_contact:
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
            existing_contact = self.find_contact_by_details(first_name, family_name, sn_code=sn_code)
            # Check if the contact already exists
            if existing_contact:
                # If the contact exists, update it
                print(f"Contact {first_name} {family_name} with SN Code {sn_code} already exists, updating it...")
                data['etag'] = existing_contact['etag']
                updated_contact = self.service.people().updateContact(
                    resourceName=existing_contact['resourceName'],
                    updatePersonFields='names,emailAddresses,phoneNumbers,addresses,userDefined',
                    body=data).execute()
                return updated_contact
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

    def batch_create_new_patients_max_200(self, patients):
        if len(patients) > 200:
            raise Exception("You can only create 200 contacts at a time")
        contacts_to_create_in_batches = []
        for patient in patients:
            new_contact = {
                'contactPerson': {
                    "names": [{
                        "givenName": patient.first_name,
                        "familyName": patient.name,
                    }],
                    "phoneNumbers": [
                        {
                            "value": patient.phone_number,
                            "type": "mobile"
                        },
                        {
                            "value": str(
                                patient.additional_phone_number) if patient.additional_phone_number else "",
                            "type": "home"
                        },
                    ],
                    "emailAddresses": [{
                        "value": patient.email_address,
                        "type": "home"
                    }],
                    "addresses": [{
                        "streetAddress": patient.address,
                        "postalCode": patient.zipcode,
                        "city": patient.city,
                        "country": patient.country.name,
                        "type": "home"
                    }],
                    "userDefined": [
                        {
                            "key": "sn_code",
                            # remove all spaces and trim sn_code before adding it
                            "value": patient.code_sn.replace(" ", "").strip()
                        },
                        {
                            "key": "user_id",
                            "value": str(patient.id)
                        },
                        {
                            "key": "created_by",
                            "value": "inur_system"
                        }
                    ]
                }
            }

            if patient.birth_date_as_object():
                new_contact["contactPerson"]["birthdays"] = [
                    {
                        "date": {
                            "year": patient.birth_date_as_object().year,
                            "month": patient.birth_date_as_object().month,
                            "day": patient.birth_date_as_object().day
                        },
                        'metadata': {'primary': True}
                    }]
            else:
                from invoices.notifications import notify_system_via_google_webhook
                print("Patient %s has no birth date" % patient)
                notify_system_via_google_webhook(
                   "*WARNING* While creating patient on Google contacts, we noticed that Patient %s has no birth date" % patient)
            contacts_to_create_in_batches.append(new_contact)
        # Make the request
        print("Creating %s new Clients by Batch ..." % len(contacts_to_create_in_batches))
        response = self.service.people().batchCreateContacts(
            body={
                'contacts': contacts_to_create_in_batches,
                'readMask': 'names,emailAddresses'  # fields to return in the response
            }
        ).execute()
        print("Batch create result: %s" % response)
        created_people = response.get('createdPeople', [])
        resource_names = [person['person']['resourceName'] for person in created_people]
        clients_group_id = self.get_or_create_contact_group("Clients")
        response = self.service.contactGroups().members().modify(
            resourceName=clients_group_id,
            body={
                'resourceNamesToAdd': resource_names
            }
        ).execute()
        print("Group add result: %s" % response)
    def batch_create_new_patients(self, patients):
        # divide the contacts into batches of 200
        print("Creating %s new Clients..." % len(patients))
        batches = [patients[i:i + 200] for i in range(0, len(patients), 200)]
        for batch in batches:
            self.batch_create_new_patients_max_200(batch)
    def create_or_update_new_patient(self, patient):
        new_contact = {
            "names": [{
                "givenName": patient.first_name,
                "familyName": patient.name,
            }],
            "phoneNumbers": [
                {
                    "value": patient.phone_number,
                    "type": "mobile"
                },
                {
                    "value": str(patient.additional_phone_number) if patient.additional_phone_number else "",
                    "type": "home"
                },
            ],
            "emailAddresses": [{
                "value": patient.email_address,
                "type": "home"
            }],
            "addresses": [{
                "streetAddress": patient.address,
                "postalCode": patient.zipcode,
                "city": patient.city,
                "country": patient.country.name,
                "type": "home"
            }],
            "userDefined": [
                {
                    "key": "sn_code",
                    # remove all spaces and trim sn_code before adding it
                    "value": patient.code_sn.replace(" ", "").strip()
                },
                {
                    "key": "user_id",
                    "value": str(patient.id)
                },
                {
                    "key": "created_by",
                    "value": "inur_system"
                }
            ]
        }
        if patient.birth_date:
            new_contact["birthdays"] = [
                {
                    "date": {
                        "year": patient.birth_date_as_object().year,
                        "month": patient.birth_date_as_object().month,
                        "day": patient.birth_date_as_object().day
                    },
                    'metadata': {'primary': True}
                }]
        else:
            from invoices.notifications import notify_system_via_google_webhook
            notify_system_via_google_webhook(
                "*WARNING* While creating patient on Google contacts, we noticed that Patient %s has no birth date" % patient)
        print("Creating new Client: %s" % new_contact)
        response = self.add_or_update_contact(new_contact)
        # Get the resource name (id) of the contact that was just added
        if response:
            from invoices.notifications import notify_system_via_google_webhook
            contact_id = response['resourceName']
            # Get the id of the "Clients" group, or create it if it doesn't exist
            group_id = self.get_or_create_contact_group("Clients")
            # Add the contact to the group
            self.add_contact_to_group(contact_id, group_id)
            notify_system_via_google_webhook(
                "Patient %s created on Google contacts for email %s and assigned to group %s" % (
                    patient, self.email, group_id))

    def create_new_employee(self, employee):
        new_contact_employee = {
            "names": [
                {  # Capitalize only first letter of first name all other letters are lower case
                    "givenName": employee.user.first_name.lower().capitalize(),
                    # CAPITALIZE LAST NAME
                    "familyName": employee.user.last_name.upper()
                }
            ],
            "emailAddresses": [
                {
                    "value": employee.user.email,
                },
                {
                    "value": employee.personal_email,
                }
            ],
            "phoneNumbers": [
                {
                    "value": str(employee.phone_number) if employee.phone_number else "",
                    "type": "mobile"
                },
                {
                    "value": str(employee.additional_phone_number) if employee.additional_phone_number else "",
                    "type": "phone"
                },
            ],
            "userDefined": [
                {
                    "key": "sn_code",
                    # check 1st if sn_code is not null and remove all spaces and trim sn_code before adding it
                    "value": employee.sn_code.replace(" ",
                                                      "").strip() if employee.sn_code else employee.generate_unique_hash()
                },
                {
                    "key": "employee_id",
                    "value": str(employee.id)
                },
                {
                    "key": "created_by",
                    "value": "inur_system"
                }
            ]

        }
        if employee.birth_date:
            new_contact_employee["birthdays"] = [
                {
                    "date": {
                        "year": employee.birth_date.year,
                        "month": employee.birth_date.month,
                        "day": employee.birth_date.day
                    },
                    'metadata': {'primary': True}
                }]
        else:
            from invoices.notifications import notify_system_via_google_webhook
            notify_system_via_google_webhook(
                "*WARNING* While creating employee on Google contacts, we noticed that Employee %s has no birth date" % employee)
        print("Creating employee: %s" % new_contact_employee)
        response = self.add_or_update_contact(new_contact_employee)
        # Get the resource name (id) of the contact that was just added
        if response:
            contact_id = response['resourceName']
            # Get the id of the "Employees" group, or create it if it doesn't exist
            group_id = self.get_or_create_contact_group("Equipe SUR.lu")
            # Add the contact to the group
            self.add_contact_to_group(contact_id, group_id)

    def delete_patient_by_details(self, first_name, family_name, sn_code):
        contact = self.find_contact_by_details(first_name, family_name, sn_code=sn_code)
        if contact:
            result = self.delete_contact(contact['resourceName'])
            print(f"Contact {first_name} {family_name} with SN Code {sn_code} deleted: {result}")
            from invoices.notifications import notify_system_via_google_webhook
            notify_system_via_google_webhook(
                "Patient %s %s with SN Code %s deleted from Google contacts for email %s" % (
                    first_name, family_name, sn_code, self.email))
        else:
            print(f"Patient {first_name} {family_name} with SN Code {sn_code} not found on Google contacts of {self.email}")

    def delete_patient(self, patient):
        self.delete_patient_by_details(patient.first_name, patient.name, sn_code=patient.code_sn)

    def delete_contact(self, resource_name):
        try:
            deletion_result = self.service.people().deleteContact(resourceName=resource_name).execute()
            print(f"Contact deleted: {deletion_result}")
        except Exception as e:
            print(f"Failed to delete contact: {e}")

    def update_patient(self, patient):
        contact = self.find_contact_by_details(patient.first_name, patient.name, sn_code=patient.code_sn)
        if contact:
            contact_id = contact['resourceName']
            # Get the id of the "Clients" group, or create it if it doesn't exist
            group_id = self.get_or_create_contact_group("Clients")
            # Add the contact to the group
            self.add_contact_to_group(contact_id, group_id)
        else:
            print(f"Patient {patient} not found on Google contacts of {self.email}")

    def search_person_in_directory(self, **kwargs):
        # build query from kwargs
        query = ""
        for key, value in kwargs.items():
            query += f"{value} "
        results = self.service.people().searchDirectoryPeople(query=query).execute()
        return results.get('people', [])

@job("default", timeout=6000)
def async_create_or_update_new_patient(google_contacts_instance, patient):
    google_contacts_instance.create_or_update_new_patient(patient)
@job("default", timeout=6000)
def async_delete_patient(google_contacts_instance, patient):
    google_contacts_instance.delete_patient(patient)

    def delete_employee(self, employee):
        contact = self.find_contact_by_details(employee.user.first_name, employee.user.last_name)
        if contact:
            self.delete_contact(contact['resourceName'])
        else:
            print(f"Employee {employee} not found on Google contacts of {self.email}")
