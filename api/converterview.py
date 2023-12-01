from io import BytesIO

import chardet
from django.http import FileResponse
from requests import Response
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from invoices.parsers.csv2ofx import CSVToOFXConverter
from invoices.parsers.mt940 import MT940toOFXConverter


class MT940toOFXConverterView(APIView):
    permission_classes = [AllowAny]

    parser_class = (FileUploadParser,)

    def post(self, request):
        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name.lower()

        # Check if the uploaded file is a ZIP file
        is_zip = file_name.endswith('.zip')
        is_csv = file_name.endswith('.csv')
        converter = None

        if is_zip:
            # Handle ZIP files as binary
            file_content = uploaded_file.read()
            converter = MT940toOFXConverter(file_content, is_zip=True)
        elif is_csv:
            # Read a portion of the file to guess the encoding
            sample = uploaded_file.read(10000)  # Read first 10,000 bytes
            uploaded_file.seek(0)  # Reset file read position

            # Detect encoding
            result = chardet.detect(sample)
            encoding = result['encoding']
            # Handle CSV files as text
            file_content = uploaded_file.read().decode(encoding)
            converter = CSVToOFXConverter(file_content, is_zip=False)
        else:
            # Try decoding as UTF-8, if that fails, try another encoding
            try:
                file_content = uploaded_file.read().decode('utf-8')
            except UnicodeDecodeError:
                try:
                    file_content = uploaded_file.read().decode('ISO-8859-1')
                except:
                    return Response({"error": "Unsupported file encoding"}, status=status.HTTP_400_BAD_REQUEST)
            converter = MT940toOFXConverter(file_content)

        ofx_data = converter.convert()

        # Prepare the OFX string for download
        buffer = BytesIO()
        buffer.write(ofx_data.encode('utf-8'))
        buffer.seek(0)
        converted_file_name = file_name.replace('.mt940', '.ofx').replace('.zip', '.ofx')

        # Return the OFX file as a response
        response = FileResponse(buffer, as_attachment=True, filename=converted_file_name)
        return response
