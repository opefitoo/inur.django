import logging
import os

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from django.contrib import admin, messages
from django.core.files.base import ContentFile

from invoices.employee import EmployeeAdminFile

# Setup logging
logger = logging.getLogger(__name__)

# Retrieve AWS credentials and configuration from environment variables
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
AWS_S3_ACCESS_KEY_ID = os.getenv('AWS_S3_ACCESS_KEY_ID')
AWS_S3_SECRET_ACCESS_KEY = os.getenv('AWS_S3_SECRET_ACCESS_KEY')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_SIGNATURE_VERSION = os.getenv('AWS_S3_SIGNATURE_VERSION')
AWS_S3_ADDRESSING_STYLE = os.getenv('AWS_S3_ADDRESSING_STYLE')

# Debugging: Log environment variables (excluding sensitive information)
logger.debug(f"AWS_S3_ACCESS_KEY_ID: {AWS_S3_ACCESS_KEY_ID}")
logger.debug(f"AWS_S3_SECRET_ACCESS_KEY: {'<hidden>' if AWS_S3_SECRET_ACCESS_KEY else None}")
logger.debug(f"AWS_ACCESS_KEY_ID: {AWS_ACCESS_KEY_ID}")
logger.debug(f"AWS_SECRET_ACCESS_KEY: {'<hidden>' if AWS_SECRET_ACCESS_KEY else None}")

# Define the old and new S3 bucket names
OLD_BUCKET_NAME = 'sur.lu'
NEW_BUCKET_NAME = 'sur.lu.2023'

# Initialize a single S3 client
s3_client = boto3.client(
    's3',
    endpoint_url=AWS_S3_ENDPOINT_URL,
    aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY,
    config=boto3.session.Config(
        signature_version=AWS_S3_SIGNATURE_VERSION,
        s3={'addressing_style': 'path'}
    )
)

@admin.action(description='Recover and re-upload files from old S3 bucket')
def recover_files_from_old_s3(modeladmin, request, queryset):
    for employee in queryset:
        for file_instance in EmployeeAdminFile.objects.filter(employee=employee):
            try:
                # Check if the file is accessible in the new bucket
                s3_client.head_object(Bucket=NEW_BUCKET_NAME, Key=file_instance.file_upload.name)
                print(f"File {file_instance.file_upload.name} is accessible in the new S3 bucket.")
                continue  # File is accessible, no need to recover

            except ClientError as e:
                # Check if the error is because the object does not exist (404)
                if e.response['Error']['Code'] == '404':
                    try:
                        # Attempt to recover from the old bucket
                        old_file = s3_client.get_object(Bucket=OLD_BUCKET_NAME, Key=file_instance.file_upload.name)
                        file_content = old_file['Body'].read()

                        # Re-upload the file to the new bucket
                        s3_client.put_object(Bucket=NEW_BUCKET_NAME, Key=file_instance.file_upload.name, Body=file_content)

                        # Update the file instance to point to the new bucket
                        file_instance.file_upload.save(file_instance.file_upload.name, ContentFile(file_content), save=True)
                        file_instance.save()

                        print(f"File {file_instance.file_upload.name} successfully recovered and re-uploaded from old S3 bucket to new S3 bucket.")
                        messages.success(request, f"File {file_instance.file_upload.name} successfully recovered and re-uploaded.")

                    except (NoCredentialsError, PartialCredentialsError, ClientError) as recovery_error:
                        messages.error(request, f"Failed to recover file {file_instance.file_upload.name}: {str(recovery_error)}")
                        print(f"Failed to recover file {file_instance.file_upload.name}: {str(recovery_error)}")

                else:
                    # Handle other ClientErrors that are not 404 Not Found
                    messages.error(request, f"Failed to check file {file_instance.file_upload.name}: {str(e)}")
                    print(f"Failed to check file {file_instance.file_upload.name}: {str(e)}")
