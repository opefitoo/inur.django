from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle


def basedata_view(request, obj):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="my_pdf.pdf"'

    # Create a canvas object with A4 landscape page size
    c = canvas.Canvas(response, pagesize=landscape(A4))

    # Define the table data as a list of rows
    data = [['Column 1', 'Column 2', 'Column 3']]

    # Define the table style with borders and alignment
    style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ])

    # Create the table object and apply the style
    table = Table(data)
    table.setStyle(style)

    # Draw the table on the canvas
    table.wrapOn(c, inch, inch)
    table.drawOn(c, inch, inch)

    # Save the PDF document and close the canvas
    c.save()
    return response


# def basedata_view(self, request, object_id):
#     # Get the object with the specified ID
#     obj = self.model.objects.get(pk=object_id)
#
#     # Set up a buffer to store the PDF content
#     buffer = io.BytesIO()
#
#     # Create a canvas with the desired page size and orientation
#     c = canvas.Canvas(buffer, pagesize=landscape(A4))
#
#     # Define the dimensions of the table
#     col_width = 4.0 * cm
#     row_height = 0.75 * cm
#     num_cols = 3
#     num_rows = 1
#
#     # Define the data for the table
#     data = [
#         [obj.field1, obj.field2, obj.field3]
#     ]
#
#     # Draw the table on the canvas
#     for i in range(num_rows):
#         for j in range(num_cols):
#             c.drawString(j * col_width + 1.5 * cm, A4[1] - (i + 1) * row_height, str(data[i][j]))
#
#     # Close the canvas and retrieve the PDF content
#     c.showPage()
#     c.save()
#     buffer.seek(0)
#
#     # Return the PDF as a response
#     return FileResponse(buffer, as_attachment=False, filename='basedata.pdf')

