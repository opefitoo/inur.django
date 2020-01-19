import io
import mimetypes
import ntpath
import os
import logging

from PIL import ExifTags, Image
from gdstorage.storage import GoogleDriveStorage, GoogleDrivePermissionType, GoogleDrivePermissionRole \
    , GoogleDriveFilePermission
from googleapiclient.http import MediaInMemoryUpload


logger = logging.getLogger('testlogger')


class CustomizedGoogleDriveStorage(GoogleDriveStorage):
    INVOICEITEM_BATCH_FOLDER = 'Invoice Item Batch'
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

    # save is overwritten as origin one sets filename equal to full path
    def save_file(self, path, content):
        logger.info('saving file %s' % path)
        self._save(path, content)

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
        try:
            image = Image.open(content.file)
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = dict(image._getexif().items())
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            # cases: image don't have getexif
            logger.error('cannot rotate image, image may not have getexif')
        imgByteArr = io.BytesIO()
        width = 600
        wpercent = (width / float(image.size[0]))
        hsize = int((float(image.size[1]) * float(wpercent)))
        logger.info('resizing image %s' % image)
        image = image.resize((width, hsize), Image.ANTIALIAS)
        image.save(imgByteArr, format=mime_type[0].split('/')[1])
        logger.info('image saved in %s' % imgByteArr)
        media_body = MediaInMemoryUpload(imgByteArr.getvalue(), mime_type, resumable=True, chunksize=1024 * 512)
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

    @staticmethod
    def _get_permission(email):
        permission = GoogleDriveFilePermission(
            GoogleDrivePermissionRole.WRITER,
            GoogleDrivePermissionType.USER,
            email
        )

        return permission
