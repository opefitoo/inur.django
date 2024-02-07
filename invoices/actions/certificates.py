from datetime import datetime
from zoneinfo import ZoneInfo

from constance import config
from django.http import HttpResponse
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph


def generate_pdf(queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    response['Content-Disposition'] = 'attachment; filename="certificat-w-%s.pdf"' % queryset[0].abbreviation

    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    elements = [Spacer(1, 20)]
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    titlist = ParagraphStyle('titlist',
                             fontName="Helvetica-Bold",
                             fontSize=16,
                             parent=styles['Heading2'],
                             alignment=TA_CENTER,
                             spaceAfter=14)
    elements.append(Paragraph(
        u"Certificat de Travail",
        titlist))
    elements.append(Spacer(6, 20))
    elements.append(Paragraph(
        u"Par la présente, le soussigné certifie que     :     %s %s" % (
        queryset[0].user.last_name, queryset[0].user.first_name),
        styles['Justify']))
    elements.append(Spacer(2, 20))
    elements.append(Paragraph(u"Demeurant à      :       %s" % queryset[0].address, styles['Justify']))
    elements.append(Spacer(2, 20))
    elements.append(Paragraph(
        u"a été au service de %s" % config.NURSE_NAME,
        styles['Justify']))
    elements.append(Spacer(3, 20))
    w_positions = queryset[0].employeecontractdetail_set.order_by('end_date').all()
    for w_position in w_positions:
        if w_position.end_date is not None:
            elements.append(Paragraph(
                u"du %s au %s %s h./semaine en qualité de : %s" % (w_position.start_date.strftime('%d/%m/%Y'),
                                                                   w_position.end_date.strftime('%d/%m/%Y'),
                                                                   w_position.number_of_hours,
                                                                   queryset[0].occupation),
                styles['Justify']))
        else:
            elements.append(Paragraph(
                u"du %s jusqu´à présent %s h./semaine en qualité de : %s" % (w_position.start_date.strftime('%d/%m/%Y'),
                                                                             w_position.number_of_hours,
                                                                             queryset[0].occupation),
                styles['Justify']))
            # add another paragraph that stipulates that employee needs to respect professional secrecy
            elements.append(Spacer(2, 20))
            elements.append(Paragraph(
                u"L'employé est tenu de respecter le secret professionnel et de ne pas divulguer des informations "
                u"confidentielles concernant les usagers (patients), les collègues et l'entreprise.",
                styles['Justify']))
        elements.append(Spacer(1, 20))
    dt_now_aware = datetime.now().astimezone(ZoneInfo("Europe/Luxembourg"))  # 1
    elements.append(Paragraph(
        u"Etabli à Luxembourg, le %s" % dt_now_aware.strftime('%d/%m/%Y'),
        styles['Justify']))
    elements.append(Spacer(8, 40))
    elements.append(Paragraph("..............................................", styles['Right']))
    doc.build(elements)
    return response
