from io import BytesIO

from django.http import FileResponse
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from invoices.parsers.mt940 import MT940toOFXConverter


class MT940toOFXConverterView(APIView):
    permission_classes = [AllowAny]

    parser_class = (FileUploadParser,)

    def post(self, request):
        uploaded_file = request.FILES['file']
        file_content = uploaded_file.read().decode('utf-8')
        converter = MT940toOFXConverter(file_content)
        ofx_data = converter.convert()  # Assuming you have a convert method

        # Prepare the OFX string for download
        buffer = BytesIO()
        buffer.write(ofx_data.encode('utf-8'))
        buffer.seek(0)
        converted_file_name = uploaded_file.name.replace('.mt940', '.ofx')

        # Return as a file response
        return FileResponse(buffer, as_attachment=True, filename=converted_file_name, content_type='application/x-ofx')
