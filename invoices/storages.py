import os
import mimetypes
import ntpath

from apiclient.http import MediaIoBaseUpload
from gdstorage.storage import GoogleDriveStorage, GoogleDrivePermissionType, GoogleDrivePermissionRole, GoogleDriveFilePermission


class CustomizedGoogleDriveStorage(GoogleDriveStorage):
    MEDICAL_PRESCRIPTION_FOLDER = 'Medical Prescription'

    def _set_permissions(self):
        from invoices.timesheet import Employee
        
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
        media_body = MediaIoBaseUpload(content.file, mime_type, resumable=True, chunksize=1024*512)
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

    def update_folder_permissions(self, path, email, has_access):
        folder_data = self._check_file_exists(path)
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

    @staticmethod
    def _get_permission(email):
        permission = GoogleDriveFilePermission(
            GoogleDrivePermissionRole.READER,
            GoogleDrivePermissionType.USER,
            email
        )

        return permission
