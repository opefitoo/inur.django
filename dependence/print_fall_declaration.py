

import io
import locale
from textwrap import wrap

from constance import config
from django.http import HttpResponse
# report lab library
from django.utils.translation import gettext as _
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm, inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph

from dependence.enums import falldeclaration_enum


def get_fall_mobility_disability(mobility_disability):
    choices = falldeclaration_enum.FallmMbilityDisability.choices
    for choice in choices:
        if mobility_disability == choice[0]:
            return _(choice[1])
    return ""


def get_medications_risk_factor_display(medications_risk_factor):

    choices = falldeclaration_enum.FallMedicationsRiskFactors.choices
    for choice in choices:
        if medications_risk_factor == choice[0]:
            return _(choice[1])
    return ""


def get_fall_circumstance_display(fall_circumstance_d):
    choices = falldeclaration_enum.FallCircumstances.choices
    for choice in choices:
        if fall_circumstance_d == choice[0]:
            return _(choice[1])
    return ""


def get_fall_consequence_display(fall_consequence_as_str):
    a_fall_consequence = falldeclaration_enum.FallConsequences(
        fall_consequence_as_str)
    if a_fall_consequence:
        return dict(falldeclaration_enum.FallConsequences.choices)[a_fall_consequence]
    return ''


def get_fall_cognitive_mood_diorders_display(fall_cognitive_mood_diorders_as_str):
    a_fall_cognitive_mood_diordersequence = falldeclaration_enum.FallCognitiveMoodDiorders(
        fall_cognitive_mood_diorders_as_str)
    if a_fall_cognitive_mood_diordersequence:
        return dict(falldeclaration_enum.FallCognitiveMoodDiorders.choices)[a_fall_cognitive_mood_diordersequence]
    return ''


def get_fall_required_medical_acts_display(fall_required_medical_acts_as_str):
    a_fall_required_medical_acts = falldeclaration_enum.FallRequiredMedicalActs(
        fall_required_medical_acts_as_str)
    if a_fall_required_medical_acts:
        return dict(falldeclaration_enum.FallRequiredMedicalActs.choices)[a_fall_required_medical_acts]
    return ''


def get_fall_incontinences_display(fall_incontinences_as_str):
    a_fall_incontinences = falldeclaration_enum.FallIncontinences(
        fall_incontinences_as_str)
    if a_fall_incontinences:
        return dict(falldeclaration_enum.FallIncontinences.choices)[a_fall_incontinences]
    return ''


def generate_pdf_fall_declaration(objects):
    # Create a new PDF object
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report.pdf"'

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    # Create the PDF object, using the response object as its "file.
    p = canvas.Canvas(response)
    for fall_declaration in objects:

        #################        HEADER        ##########################
        #################     LOGO  + text below ########################
        # set the position and size of the logo
        # set the position and size of the logo
        # set the position and size of the logo
        logo_x = 20

        # read the image file
        logo_path = "invoices/static/images/Logo_SUR_quadri_transparent_pour_copas.png"
        logo_img = ImageReader(logo_path)

        # Read the image dimensions
        img_width, img_height = logo_img.getSize()

        # Calculate the aspect ratio
        aspect = img_height / float(img_width)

        # Set the desired width
        desired_width = 70

        # Calculate the height based on the aspect ratio and desired width
        desired_height = desired_width * aspect

        # Convert 8mm to points
        mm_to_points = 2.83465
        top_margin = 5 * mm_to_points

        # Assuming a standard letter size (11 inches tall or 792 points)
        page_height = 792

        # Adjust the y-position based on the desired height and top margin
        logo_y = page_height - desired_height - top_margin

        # Draw the image on the PDF canvas
        p.drawImage(logo_img, logo_x, logo_y, width=desired_width, height=desired_height, mask='auto')

        # add some text below the logo
        p.setFont("Helvetica-Bold", 9)

        nurse_name = config.NURSE_NAME
        nurse_code = config.MAIN_NURSE_CODE
        nurse_phone_number = config.NURSE_PHONE_NUMBER
        nurse_address = config.NURSE_ADDRESS
        nurse_zip_code_city = config.NURSE_ZIP_CODE_CITY

        patient_gender = fall_declaration.patient.gender
        patient_first_name = fall_declaration.patient.first_name
        patient_name = fall_declaration.patient.name
        patient_code_sn = fall_declaration.patient.code_sn
        patient_address = fall_declaration.patient.address
        patient_zipcode = fall_declaration.patient.zipcode
        patient_clean_phone_number = fall_declaration.patient.phone_number

        # p.drawString(logo_x,  logo_y - 15, f"{nurse_name} - ")
        # p.drawString(logo_x + 100,  logo_y - 15, f"{nurse_code}")
        # p.drawString(logo_x,  logo_y - 30, f"{nurse_address} - ")
        # p.drawString(logo_x + 90,  logo_y - 30, f"{nurse_zip_code_city}")
        # p.drawString(logo_x,  logo_y - 45, f"{nurse_phone_number}")

        if patient_gender == 'MAL':
            p.drawString(logo_x + 100,  logo_y,
                         f" Monsieur {patient_name} {patient_first_name}")
        elif patient_gender == 'FEM':
            p.drawString(logo_x + 100,  logo_y,
                         f" Madame {patient_name} {patient_first_name}")
        else:
            p.drawString(logo_x + 100,  logo_y,
                         f"{patient_name} {patient_first_name}")

        p.drawString(logo_x + 100,  logo_y - 10, f"{patient_address}")
        p.drawString(logo_x + 100,  logo_y - 20, f"{patient_zipcode}")
        p.drawString(logo_x + 100,  logo_y - 30,
                     f"Tél.:  {patient_clean_phone_number}")

        #############################   End  HEADER ####################################
        #############################   Content PDF ####################################

        # Help •••••••••••••••••••••••••••••••••••••••••••••••••••••••
        def drawMyRuler(pdf):
            pdf.drawString(100, 810, 'x100')
            pdf.drawString(200, 810, 'x200')
            pdf.drawString(300, 810, 'x300')
            pdf.drawString(400, 810, 'x400')
            pdf.drawString(500, 810, 'x500')

            pdf.drawString(10, 100, 'y100')
            pdf.drawString(10, 200, 'y200')
            pdf.drawString(10, 300, 'y300')
            pdf.drawString(10, 400, 'y400')
            pdf.drawString(10, 500, 'y500')
            pdf.drawString(10, 600, 'y600')
            pdf.drawString(10, 700, 'y700')
            pdf.drawString(10, 800, 'y800')

        # drawMyRuler(p)

        # title

        # List of Lists
        data = [["Formulaire de constat de chute"]]

        table = Table(data)

        p.setFont('Helvetica-Bold', 16)

        style = TableStyle([
            ('BACKGROUND', (0, 0), (3, 0), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            # ('FONTNAME', (0,0), (-1,0), 'Courier-Bold'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
        ])
        table.setStyle(style)

        # Calculate the width and height of the table
        width, height = table.wrapOn(p, inch, inch)
        # Calculate the x and y coordinates to center the title on the canvas
        x = (8 * inch - width) / 2
        y = (19.5 * inch - height) / 2

        # Draw the table on the canvas
        table.drawOn(p, x, y)

        title_x = 298
        title_y = 670

        p.setFont('Helvetica-Bold', 9)
        #p.drawString(50, title_y, "À remplir : après chaque chute.")

        # A •••••••••••••••••••••••••••••••••••••••••••••••••••••••

        A_y = title_y - 40

        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

        date_fall = fall_declaration.datetimeOfFall  # Example date for demonstration
        formatted_date_fall = date_fall.strftime("%d %B %Y %H:%M")

        place_fall = fall_declaration.placeOfFall

        declared_by_fall_f = fall_declaration.declared_by.user.first_name
        declared_by_fall_n = fall_declaration.declared_by.user.last_name

        witness_fall = fall_declaration.witnesses

        def witnesses_value():
            if witness_fall:
                return f"Témoins éventuels: {witness_fall}"
            else:
                return "Aucun Témoins"
        # -----------------------------------------------------------------

        # List of Lists
        styles = getSampleStyleSheet()
        # Create a justified text style
        justified_style = styles["BodyText"]
        justified_style.alignment = TA_JUSTIFY

        data = [[Paragraph(f"A. Date, heure de la chute: {formatted_date_fall}", justified_style),
                 Paragraph(f"Lieu de la chute:  {place_fall}", justified_style)],
                [Paragraph(f"Déclaré par:{declared_by_fall_f} {declared_by_fall_n}", justified_style),
                 Paragraph(witnesses_value(), justified_style)],
                ]

        # Adjusted colWidths to split the width evenly between the two columns
        table = Table(data, colWidths=[240, 240])

        p.setFont('Helvetica-Bold', 9)

        # Add borders
        ts = TableStyle(
            [
                ('BACKGROUND', (0, 0), (1, 0), colors.green),  # Adjusted column index
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]
        )
        table.setStyle(ts)

        # Calculate the width and height of the table
        width, height = table.wrapOn(p, inch, inch)
        # Calculate the x and y coordinates to center the title on the canvas
        x = (7.5 * inch - width) / 2
        y = (17.8 * inch - height) / 2

        # Draw the table on the canvas
        table.drawOn(p, x, y)

        # B •••••••••••••••••••••••••••••••••••••••••••••••••••••••

        B_y = title_y - 73

        fall_circumstance = fall_declaration.fall_circumstance
        fall_circumstance_d = get_fall_circumstance_display(fall_circumstance)
        ot_fall_circumstance = fall_declaration.other_fall_circumstance


        # Set up the text style
        text_style = p.beginText()
        text_style.setFont("Helvetica-Bold", 9)
        text_style.setFillColor("black")

        # create a text object
        textobject = p.beginText()
        textobject.setTextOrigin(50, B_y - 21)

        str_fall = "• " + str(fall_circumstance_d)
        wraped_text = "\n".join(wrap(str_fall, 30))

        # wrap the text into lines using the textLines() method
        lines = textobject.textLines(wraped_text)

        def fall_circumstance_value():
            if fall_circumstance != "FCI_OTHER_CAUSES":
                return str_fall
            else:
                return f"{ot_fall_circumstance}"

        fall_incident_circumstance = fall_declaration.incident_circumstance

        # -----------------------------------------------------------------

        # List of Lists
        styles = getSampleStyleSheet()
        # Create a justified text style
        justified_style = styles["BodyText"]
        justified_style.alignment = TA_JUSTIFY

        data = [["B. Circonstances de la chute"],
                [Paragraph(fall_circumstance_value(), justified_style)],
                [Paragraph(f"Circonstances de l’incident:{fall_incident_circumstance}", justified_style)],
                ]

        table = Table(data, colWidths=480)  # Removed rowHeights

        # Add borders
        ts = TableStyle(
            [
                ('BACKGROUND', (0, 0), (3, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]
        )
        table.setStyle(ts)

        # Calculate the width and height of the table
        width, height = table.wrapOn(p, inch, inch)
        # Calculate the x and y coordinates to center the title on the canvas
        x = (7.5 * inch - width) / 2
        y = (16.3 * inch - height) / 2

        # Draw the table on the canvas
        table.drawOn(p, x, y)

        # C ••••••••••••••••••••••••••••••••••••••••••••••••••••••••

        C_y = title_y - 140
        f_other_fall_consequence = fall_declaration.other_fall_consequence

        # Set up the styles for the table
        styles = getSampleStyleSheet()
        style_normal = styles['Normal']
        styleN = styles["BodyText"]
        styleN.alignment = TA_LEFT
        # List of Lists

        data = [["C. Conséquences de la chute", "", ""],
                ]
        con_X = 30
        consequence_array = []
        for consequence in eval(fall_declaration.fall_consequences):
            if consequence:
                consequence_display = get_fall_consequence_display(
                    fall_consequence_as_str=consequence)
                consequence_cell = Paragraph(
                    f"   • {_(consequence_display)}", styleN)
                consequence_array.append(consequence_cell)
                con_X += 130
        chunk_size = 3
        consequence_lines = 0
        while consequence_array:
            consequence_lines += 1
            chunk, consequence_array = consequence_array[:
                                                         chunk_size], consequence_array[chunk_size:]
            data.append(chunk)

        if f_other_fall_consequence:
            data.append([f" Autres conséquences :   {f_other_fall_consequence}"])
        # -----------------------------------------------------------------
        cell_width = 0.1*inch
        cell_height = 0.1*inch
        table = Table(data, colWidths=[57*mm, 63*mm, 49*mm], rowHeights=None)
        span_other_consequences = consequence_lines+1
        # Add borders
        ts = TableStyle(
            [
                ('BACKGROUND', (0, 0), (3, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('SIZE', (0, 0), (-1, -1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('SPAN', (0, 0), (2, 0)),
                ('SPAN', (0, span_other_consequences),
                 (2, span_other_consequences)),
            ]
        )

        table.setStyle(ts)

        # plus que 03 chopix en ajoute une ligne

        # Calculate the width and height of the table
        width, height = table.wrapOn(p, inch, inch)

        # Calculate the x and y coordinates to center the title on the canvas
        x = (7.5 * inch - width) / 2
        y = (14.2 * inch - height) / 2

        # Draw the table on the canvas
        table.drawOn(p, x, y)

        # D ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••

        D_y = title_y - 200

        # List of Lists

        data = [["D. Actes médicaux et/ou infirmiers requis dans les 24h (plusieurs réponses possibles)", "", ""],
                ]

        fall_other_required_medical_act = fall_declaration.other_required_medical_act

        medical_act_display_array = []

        med_x = 30
        for medical_act in eval(fall_declaration.fall_required_medical_acts):
            if medical_act:
                medical_act_display = get_fall_required_medical_acts_display(
                    fall_required_medical_acts_as_str=medical_act)
                medical_act_cell = Paragraph(
                    f"   • {_(medical_act_display)}", styleN)
                medical_act_display_array.append(medical_act_cell)
                med_x += 130

        chunk_size = 3
        medical_act_lines = 0
        while medical_act_display_array:
            medical_act_lines += 1
            chunk, medical_act_display_array = medical_act_display_array[
                :chunk_size], medical_act_display_array[chunk_size:]
            data.append(chunk)

        if fall_other_required_medical_act:
            data.append([f" Autres actes médicaux :   {fall_other_required_medical_act}"])

        # ------------------------------------------------------------------

        cell_width = 0.1*inch
        cell_height = 0.1*inch
        table = Table(data, colWidths=[57*mm, 63*mm, 49*mm], rowHeights=None)

        span_other_medical_act = medical_act_lines+1
        # Add borders
        ts = TableStyle(
            [
                ('BACKGROUND', (0, 0), (3, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('SIZE', (0, 0), (-1, -1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                # merge the First row
                ('SPAN', (0, 0), (2, 0)),
                # merge the third row
                ('SPAN', (0, span_other_medical_act), (2, span_other_medical_act)),
            ]
        )
        table.setStyle(ts)

        # Calculate the width and height of the table
        width, height = table.wrapOn(p, inch, inch)

        # Calculate the x and y coordinates to center the title on the canvas
        x = (7.5 * inch - width) / 2
        y = (11.8 * inch - height) / 2

        # Draw the table on the canvas
        table.drawOn(p, x, y)

        # E  •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••

        # List of Lists

        dataE = [["E. Facteurs de risque", "", ""]]

        E_y = title_y - 260

        fall_medications_risk_factor = get_medications_risk_factor_display(
            fall_declaration.medications_risk_factor)
        # ----------------------------------------------------
        # ****************************************************
        # 1 --------------------------------------------------

        if fall_medications_risk_factor:
            dataE.append([f"  • {fall_medications_risk_factor}"])
        # ----------------------------------------------------
        # ****************************************************
        # 2 ----------------------------------------------------
        dataE.append(["   Troubles cognitifs et/ou de l’humeur"])

        trouble_array = []
        tro_x = 30
        for trouble in eval(fall_declaration.fall_cognitive_mood_diorders):
            if trouble:
                trouble_display = get_fall_cognitive_mood_diorders_display(
                    fall_cognitive_mood_diorders_as_str=trouble)
                trouble_cell = Paragraph(f"   • {_(trouble_display)}", styleN)
                trouble_array.append(trouble_cell)
                tro_x += 130

        chunk_size = 3
        trouble_lines = 2
        while trouble_array:
            trouble_lines += 1
            chunk, trouble_array = trouble_array[:
                                                 chunk_size], trouble_array[chunk_size:]
            dataE.append(chunk)

        # ----------------------------------------------------
        # ****************************************************
        # 3 --------------------------------------------------

        dataE.append(["   Incontinence"])
        incontinence_array = []
        inc_x = 30
        for incontinence in eval(fall_declaration.fall_incontinences):
            if incontinence:
                incontinence_display = get_fall_incontinences_display(
                    fall_incontinences_as_str=incontinence)
                incontinence_cell = Paragraph(
                    f"  • { _(incontinence_display)}", styleN)
                incontinence_array.append(incontinence_cell)
                inc_x += 130

        dataE.append(incontinence_array)

        # ----------------------------------------------------
        # ****************************************************
        # 4 --------------------------------------------------
        dataE.append(["   Incapacité concernant les déplacements"])
        fall_mobility_disability = get_fall_mobility_disability(
            fall_declaration.mobility_disability)
        if fall_mobility_disability:
            dataE.append([f" • {fall_mobility_disability}"])

        # ----------------------------------------------------
        # ****************************************************
        # 5 --------------------------------------------------
        fall_unsuitable_footwear = fall_declaration.unsuitable_footwear
        if fall_unsuitable_footwear:
            dataE.append(["   Chaussures inadaptées: Oui"])
        else:
            dataE.append(["   Chaussures inadaptées: Non"])

        # ----------------------------------------------------
        # ****************************************************
        # 6 --------------------------------------------------
        fall_other_contributing_factor = fall_declaration.other_contributing_factor

        if fall_other_contributing_factor:
            dataE.append(
                [f"   Autre facteur favorisant:{fall_other_contributing_factor}"])

        # ------------------------------------------------------------------

        cell_width = 0.1*inch
        cell_height = 0.1*inch
        table = Table(dataE, colWidths=[57*mm, 63*mm, 49*mm], rowHeights=None)
        span_other_trouble = trouble_lines + 1  # Incontinence

        # Add borders
        ts = TableStyle(
            [
                ('BACKGROUND', (0, 0), (3, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('SIZE', (0, 0), (-1, -1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                # merge the First row
                ('SPAN', (0, 0), (2, 0)),  # E. Facteurs de risque
                ('SPAN', (0, 1), (2, 1)),  # Médicaments
                ('SPAN', (0, 2), (2, 2)),  # Troubles cognitifs et/ou de l’humeur
                # 3eme ligne • Agitation
                ('SPAN', (0, span_other_trouble),
                 (2, span_other_trouble)),  # Incontinence
                # Incapacité concernant les déplacements
                ('SPAN', (0, span_other_trouble + 2), (2, span_other_trouble + 2)),
                # se déplace seul avec difficulté avec ou sans moyens auxiliaire
                ('SPAN', (0, span_other_trouble + 3), (2, span_other_trouble + 3)),
                ('SPAN', (0, span_other_trouble + 4),
                 (2, span_other_trouble + 4)),  # chaussures inadapté
                # Autre facteur favorisant:
                ('SPAN', (0, span_other_trouble + 5), (2, span_other_trouble + 5)),


                # merge the fifth row
            ]
        )
        table.setStyle(ts)

        # Calculate the width and height of the table
        width, height = table.wrapOn(p, inch, inch)

        # Calculate the x and y coordinates to center the title on the canvas
        x = (7.5 * inch - width) / 2
        y = (7.5 * inch - height) / 2

        # Draw the table on the canvas
        table.drawOn(p, x, y)

        # F •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••

        dataFG = []

        F_y = title_y - 500
        fall_preventable_fall = fall_declaration.preventable_fall
        if fall_preventable_fall:
            dataFG.append(["F. La chute aurait pu être prévenue : Oui"])
        else:
            dataFG.append(["F. La chute aurait pu être prévenue : Non"])

        # G •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
        G_y = title_y - 530
        fall_physician_informed = fall_declaration.physician_informed
        if fall_physician_informed:
            dataFG.append(["G. Le médecin a été avisé :  Oui"])
        else:
            dataFG.append(["G. Le médecin a été avisé :  Non"])

        # ------------------------------------------------------------------

        cell_width = 0.1*inch
        cell_height = 0.1*inch
        table = Table(dataFG, colWidths=480, rowHeights=20)

        # Add borders
        ts = TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('SIZE', (0, 0), (-1, -1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]
        )
        table.setStyle(ts)

        # Calculate the width and height of the table
        width, height = table.wrapOn(p, inch, inch)

        # Calculate the x and y coordinates to center the title on the canvas
        x = (7.5 * inch - width) / 2
        y = (3.7 * inch - height) / 2

        # Draw the table on the canvas
        table.drawOn(p, x, y)

        # Close the PDF object cleanly, and we're done.
        # Pagination

        # page_num = p.getPageNumber()
        # text = "page %s" % page_num
        # p.drawString(300, 20, text)

        # Move to the next page For other patient
        p.showPage()

    # Save the PDF
    p.save()

    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response
