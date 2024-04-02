import os
import traceback
from tempfile import NamedTemporaryFile

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

from invoices import settings
from invoices.notifications import notify_system_via_google_webhook


class ReportChatSending:
    SCOPES = ["https://www.googleapis.com/auth/chat.messages",]

    def __init__(self, json_keyfile_path=None, email=None):
        self.credential_file = settings.GOOGLE_CHAT_IMG_JSON
        self.email = email
        self.CREDENTIALS = None
        self._init_service()
        # self.service = build('chat', 'v1', credentials=self.creds)
        self.service = build('chat', 'v1', credentials=self.creds)

    def _init_service(self):
        credentials = service_account.Credentials.from_service_account_file(
            self.credential_file, scopes=self.SCOPES, subject=self.email)
        # if self.email:
        #     delegated_credentials = credentials.with_subject(os.environ.get(self.email, None))
        #
        # else:
        if self.email:
            delegated_credentials = credentials.with_subject(self.email)
        else:
            delegated_credentials = credentials.with_subject(os.environ.get('GOOGLE_CHAT_EMAIL', None))
        self.creds = delegated_credentials

    def send_text(self, message, event=None):
        try:
            # The space ID, e.g., 'spaces/AAAABpdRn_k'
            space_id = os.environ.get('GOOGLE_SPACE_NAME', None)

            # Create a Chat message with attachment.
            result = self.service.spaces().messages().create(
                # The space to create the message in.
                #
                # Replace SPACE with a space name.
                # Obtain the space name from the spaces resource of Chat API,
                # or from a space's URL.
                #
                # Must match the space name that the attachment is uploaded to.
                parent=space_id,

                # The message to create.
                body={
                    'text': message,
                }

            ).execute()
            print("Message created: %s" % result)
            from invoices.events import Event
            event.google_chat_message_id = result['name']
            event._update_without_signals = True
            event.save()
            return result
        except Exception as e:
            error_detail = traceback.format_exc()
            notify_system_via_google_webhook(
                "*An error occurred sending an event report: {0}*\nDetails:\n{1}".format(e, error_detail))

    def update_text(self, message, google_chat_message_id=None):
        try:
            # The space ID, e.g., 'spaces/AAAABpdRn_k'
            space_id = os.environ.get('GOOGLE_SPACE_NAME', None)

            # Create a Chat message with attachment.
            result = self.service.spaces().messages().update(
                name=google_chat_message_id,
                updateMask='text,attachment',
                body={
                    'text': message,
                }
            ).execute()
            print("Message created: %s" % result)
            return result
        except Exception as e:
            error_detail = traceback.format_exc()
            notify_system_via_google_webhook(
                "*An error occurred sending an event report: {0}*\nDetails:\n{1}".format(e, error_detail))

def download_file(url):
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        with NamedTemporaryFile(delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                temp_file.write(chunk)
            return temp_file.name
    else:
        raise Exception("Failed to download file")
