import mimetypes
import logging
import mimetypes
import ntpath
import os

from gdstorage.storage import GoogleDriveStorage, GoogleDrivePermissionType, GoogleDrivePermissionRole \
    , GoogleDriveFilePermission
from apiclient import errors
from googleapiclient.http import MediaIoBaseUpload
from rq import Queue

from worker import conn

logger = logging.getLogger(__name__)


class CustomizedGoogleDriveStorage(GoogleDriveStorage):
    INVOICEITEM_BATCH_FOLDER = 'Invoice Item Batch'
    MEDICAL_PRESCRIPTION_FOLDER = 'Medical Prescription'

    def _set_permissions(self):
        from invoices.employee import Employee

        if not self._permissions:
            employees = Employee.objects.filter(has_gdrive_access=True)
            for employee in employees:
                email = employee.user.email
                if email:
                    self._permissions.append(self._get_permission(email))

    def __init__(self):
        super(CustomizedGoogleDriveStorage, self).__init__()

    def get_thumbnail_link(self, file_name):
        gdrive_size_suffix = '=s220'
        link = ''
        if file_name and file_name is not None:
            file_info = self._check_file_exists(file_name)
            if file_info is not None and 'thumbnailLink' in file_info:
                link = file_info['thumbnailLink'].replace(gdrive_size_suffix, '')

        return link

    # save is overwritten as origin one sets filename equal to full path
    def save_file(self, path, content):
        print('p saving file %s' % path)
        logger.info('saving file %s' % path)
        q = Queue(connection=conn)
        q.enqueue(self._save, path, content)

    # _save is overwritten as origin one sets filename equal to full path
    def _save(self, path, content):
        self._set_permissions()
        folder_path = os.path.sep.join(self._split_path(path)[:-1])
        folder_data = self._get_or_create_folder(folder_path)
        parent_id = None if folder_data is None else folder_data['id']
        filename = ntpath.basename(path)
        # Now we had created (or obtained) folder on GDrive
        # Upload the file
        mime_type = mimetypes.guess_type(filename)
        if mime_type[0] is None:
            mime_type = self._UNKNOWN_MIMETYPE_
        media_body = MediaIoBaseUpload(content.file, mime_type, resumable=True, chunksize=1024 * 512)
        body = {
            'title': filename,
            'mimeType': mime_type
        }
        # Set the parent folder.
        if parent_id:
            body['parents'] = [{'id': parent_id}]
        file_data = self._drive_service.files().insert(
            body=body,
            media_body=media_body).execute()

        # Setting up permissions
        for p in self._permissions:
            self._drive_service.permissions().insert(fileId=file_data["id"], body=p.raw).execute()

        return file_data.get(u'originalFilename', file_data.get(u'title'))

    def update_file_description(self, path, description):
        body = {'description': description}
        file_data = self._check_file_exists(path)
        if file_data is not None:
            self._drive_service.files().update(fileId=file_data["id"], body=body).execute()

    def update_folder_permissions(self, path, email, has_access):
        folder_data = self._get_or_create_folder(path)
        folder_permissions = self._drive_service.permissions().list(fileId=folder_data["id"]).execute()
        user_permissions = [d for d in folder_permissions['items'] if d.get('emailAddress', '') == email]
        permissions_granted = len(user_permissions)
        if folder_data is not None:
            if has_access and 0 == permissions_granted:
                p = self._get_permission(email)
                self._drive_service.permissions().insert(fileId=folder_data["id"], body=p.raw).execute()
            elif not has_access and 0 < permissions_granted:
                for user_permission in user_permissions:
                    self._drive_service.permissions().delete(fileId=folder_data["id"],
                                                             permissionId=user_permission['id']).execute()
            self._set_permissions()
        else:
            return None

    def update_folder_permissions_v3(self, path, email, has_access):
        folder_data = self._get_or_create_folder(path)
        folder_permissions = self._drive_service.permissions().list(fileId=folder_data["id"], fields='*').execute()
        user_permissions = [d for d in folder_permissions['permissions'] if d.get('emailAddress', '') == email]
        permissions_granted = len(user_permissions)
        if folder_data is not None:
            if has_access and 0 == permissions_granted:
                p = self._get_permission(email)
                self._drive_service.permissions().insert(fileId=folder_data["id"], body=p.raw).execute()
            elif not has_access and 0 < permissions_granted:
                for user_permission in user_permissions:
                    self._drive_service.permissions().delete(fileId=folder_data["id"],
                                                             permissionId=user_permission['id']).execute()
                self._set_permissions()
            else:
                return None

    def insert_permission(self, path, value, perm_type, role):
        """Insert a new permission.

        Args:
          path: Path of the file to insert permission for.
          value: User or group e-mail address, domain name or None for 'default'
                 type.
          perm_type: The value 'user', 'group', 'domain' or 'default'.
          role: The value 'owner', 'writer' or 'reader'.
        Returns:
          The inserted permission if successful, None otherwise.
        """
        file = self._get_or_create_folder(path)
        file_id = file['id']
        new_permission = {
            'value': value,
            'type': perm_type,
            'role': role,
            'emailAddress': value
        }
        try:
            return self._drive_service.permissions().create(fileId=file_id,
                                                            body=new_permission).execute()
        except errors.HttpError as error:
            print
            'An error occurred: %s' % error
        return None

    def delete_permission(self, path, permission_id):
        """Delete a permission.

        Args:
          path: Path of the file to insert permission for.
          permission_id: the Id for the permission ressource according to Google API.
        Returns:
          The inserted permission if successful, None otherwise.
        """
        file = self._get_or_create_folder(path)
        file_id = file['id']
        try:
            return self._drive_service.permissions().delete(fileId=file_id,
                                                            permissionId=permission_id).execute()
        except errors.HttpError as error:
            print
            'An error occurred: %s' % error
        return None

    @staticmethod
    def _get_permission(email):
        permission = GoogleDriveFilePermission(
            GoogleDrivePermissionRole.WRITER,
            GoogleDrivePermissionType.USER,
            email
        )

        return permission
