import os
import traceback
from tempfile import NamedTemporaryFile

import requests
from django_rq import job
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from invoices import settings
from invoices.notifications import notify_system_via_google_webhook


class ImageGoogleChatSending:
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

    @job("default", timeout=6000)
    def send_image(self, message, image_url, report_picture_id=None):
        try:


            # The space ID, e.g., 'spaces/AAAABpdRn_k'
            space_id = os.environ.get('GOOGLE_SPACE_NAME', None)

            # Attempt to get details about the space

            image_path = download_file(image_url)
            media = MediaFileUpload(image_path, mimetype='image/png')

            attachment_uploaded = self.service.media().upload(

                # The space to upload the attachment in.
                #
                # Replace SPACE with a space name.
                # Obtain the space name from the spaces resource of Chat API,
                # or from a space's URL.
                parent=space_id,

                # The filename of the attachment, including the file extension.
                body={'filename': 'test_image.png'},

                # Media resource of the attachment.
                media_body=media

            ).execute()
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
                    'attachment': [attachment_uploaded]
                }

            ).execute()
            print("Message created: %s" % result)
            from invoices.events import ReportPicture
            report_picture = ReportPicture.objects.get(id=report_picture_id)
            report_picture.google_chat_message_id = result['name']
            report_picture._update_without_signals = True
            report_picture.save()
            return result
        except Exception as e:
            error_detail = traceback.format_exc()
            notify_system_via_google_webhook(
                "*An error occurred sending an image: {0}*\nDetails:\n{1}".format(e, error_detail))

    def update_image(self, message, image_url, google_chat_message_id=None):
        try:
            # The space ID, e.g., 'spaces/AAAABpdRn_k'
            space_id = os.environ.get('GOOGLE_SPACE_NAME', None)

            # Attempt to get details about the space

            image_path = download_file(image_url)
            media = MediaFileUpload(image_path, mimetype='image/png')

            attachment_uploaded = self.service.media().upload(

                # The space to upload the attachment in.
                #
                # Replace SPACE with a space name.
                # Obtain the space name from the spaces resource of Chat API,
                # or from a space's URL.
                parent=space_id,

                # The filename of the attachment, including the file extension.
                body={'filename': 'test_image.png'},

                # Media resource of the attachment.
                media_body=media

            ).execute()
            # Create a Chat message with attachment.
            result = self.service.spaces().messages().update(
                name=google_chat_message_id,
                updateMask='text,attachment',
                body={
                    'text': message, 'attachment': [attachment_uploaded]
                }
            ).execute()
            print("Message created: %s" % result)
            return result
        except Exception as e:
            error_detail = traceback.format_exc()
            notify_system_via_google_webhook(
                "*An error occurred sending an image: {0}*\nDetails:\n{1}".format(e, error_detail))

def download_file(url):
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        with NamedTemporaryFile(delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                temp_file.write(chunk)
            return temp_file.name
    else:
        raise Exception("Failed to download file")
