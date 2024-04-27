import io

from PyPDF2 import PdfReader, PdfWriter


def extract_individual_paylip_pdf(file_obj):
    pdf_reader = PdfReader(file_obj)
    payslips = {}
    for page_number, page in enumerate(pdf_reader.pages, start=1):
        text = page.extract_text()
        for line in text.splitlines():
            if line.startswith("Classe"):
                values = line.split()
                name = " ".join(values[2:])
                # remove "ADULTE" from the name
                name = name.replace("ADULTE", "")
                name = name.replace("FAMILIALE", "")
                # remove any spaces at beginning and end of the name
                name = name.strip()
                # Teixeira Da Costa
                name = name.replace("TEIXERA", "Teixeira")
                #print(name)
                #print("Page number is %s" % page_number)

                pdf_writer = PdfWriter()
                pdf_writer.add_page(page)

                # Write the PDF data to a BytesIO object
                pdf_data_io = io.BytesIO()
                pdf_writer.write(pdf_data_io)

                # Get the binary data from the BytesIO object
                pdf_data = pdf_data_io.getvalue()

                # Add the PDF data to the payslips dictionary
                payslips[name] = pdf_data

    if not payslips:
        print("No payslip found in the pdf")
    if len(payslips) != len(pdf_reader.pages):
        print("Number of payslips found is not equal to the number of pages in the pdf : payslips %s, pages %s" % (len(payslips), len(pdf_reader.pages)))
    return payslips
