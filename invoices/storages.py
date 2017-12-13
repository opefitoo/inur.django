from gdstorage.storage import GoogleDriveStorage


class CustomizedGoogleDriveStorage(GoogleDriveStorage):
    def __init__(self):
        super(CustomizedGoogleDriveStorage, self).__init__()

    def get_thumbnail_link(self, file_name):
        gdrive_size_suffix = '=s220'
        link = ''
        if file_name and file_name is not None:
            file_info = self._check_file_exists(file_name)
            if 'thumbnailLink' in file_info:
                link = file_info['thumbnailLink'].replace(gdrive_size_suffix, '')

        return link
