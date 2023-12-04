import os
from tempfile import NamedTemporaryFile

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from invoices import settings


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
            self.credential_file, scopes=self.SCOPES)
        # if self.email:
        #     delegated_credentials = credentials.with_subject(os.environ.get(self.email, None))
        #
        # else:
        delegated_credentials = credentials.with_subject(os.environ.get('GOOGLE_EMAIL_CREDENTIALS', None))
        self.creds = delegated_credentials

    def send_image(self, message, image_url):

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
            parent='spaces/AAAAggFq5Js',

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
        return result


def download_file(url):
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        with NamedTemporaryFile(delete=False) as temp_file:
            for chunk in response.iter_content(chunk_size=1024):
                temp_file.write(chunk)
            return temp_file.name
    else:
        raise Exception("Failed to download file")
