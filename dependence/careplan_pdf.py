import locale
from datetime import datetime

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, PageBreak, Table, TableStyle, Image

from dependence.careplan import CarePlanMaster, CarePlanDetail
from invoices.settings import BASE_DIR


def generate_pdf(queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm,
                            pagesize=landscape(A4))
    elements = []
    # Append invoice number and invoice date
    if len(queryset) > 1:
        for care_plan in queryset:
            elements.extend(build_doc_per_care_plan(care_plan))
            elements.append(PageBreak())
    response['Content-Disposition'] = 'attachment; filename="plan-soins-%s.pdf"' % queryset[0].patient

    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm,
                            pagesize=landscape(A4))

    doc.build(elements, onFirstPage=myFirstPage, onLaterPages=myFirstPage)
    # doc.build(elements)
    return response


def build_doc_per_care_plan(care_plan: CarePlanMaster):
    elements = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))
    patientstyle = ParagraphStyle('patientstyle',
                                  fontName="Helvetica",
                                  fontSize=12,
                                  parent=styles['Heading6'],
                                  alignment=TA_RIGHT,
                                  spaceAfter=5)
    normalstyle = ParagraphStyle('patientstyle',
                                 fontName="Helvetica",
                                 fontSize=12,
                                 parent=styles['Heading6'],
                                 alignment=TA_LEFT,
                                 spaceAfter=5)
    smallstyle = ParagraphStyle('patientstyle',
                                fontName="Helvetica",
                                fontSize=8,
                                parent=styles['Normal'],
                                alignment=TA_LEFT,
                                spaceAfter=0)
    elements.append(Paragraph(
        u"patient: %s" % care_plan.patient,
        patientstyle))
    elements.append(Paragraph(
        u"matricule: %s" % care_plan.patient.code_sn,
        patientstyle))
    titlist = ParagraphStyle('titlist',
                             fontName="Helvetica-Bold",
                             fontSize=16,
                             parent=styles['Heading2'],
                             alignment=TA_CENTER,
                             spaceAfter=14)
    elements.append(Paragraph(
        u"Plan de Soins Détaillé Conclu avec le Patient",
        titlist))
    locale.setlocale(locale.LC_ALL, 'fr_FR.utf-8')
    elements.append(Paragraph(
        u"Plan N°: %s - Dès le: %s" % (care_plan.plan_number, care_plan.plan_start_date.strftime("%d %B %Y")),
        normalstyle))
    if care_plan.replace_plan_number:
        elements.append(Paragraph(
            u"En remplacement du plan N°: %s" % care_plan.replace_plan_number,
            normalstyle))
    data = [(Paragraph("<strong>Période de la journée</strong>", smallstyle),
             Paragraph("<strong>Actions à prévoir</strong>", smallstyle))]
    i = 0
    for detail in CarePlanDetail.objects.filter(care_plan_to_master_id=care_plan.pk).order_by("id").all():
        i += 1
        data.append(
            (u"%s de %s à %s" % (detail.get_params_day_of_week_display(), detail.time_start.strftime("%H:%M"),
                                 detail.time_end.strftime("%H:%M")),
             Paragraph(str(detail.care_actions).replace('\n', '<br />\n'), smallstyle)))
    elements.append(Spacer(1, 18))
    table = Table(data, [6 * cm, 22 * cm], repeatRows=1)
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))
    elements.append(table)
    return elements


Title = "Hello world"
pageinfo = "platypus example"


def myFirstPage(canv, doc):
    img = Image('http://demoschoolzen.educationzen.com/images/tia.png')
    img.drawHeight = 0.7 * cm
    img.drawWidth = 0.7 * cm
    canv.saveState()
    canv.setPageSize(doc.pagesize)
    canv.setTitle(doc.title)

    # # header
    # canv.drawImage("invoices/static/patientanamnesis/images/logo.png",  500, 765, width=50, height=50)
    canv.drawImage(BASE_DIR + "/static/patientanamnesis/images/logo.png",  doc.pagesize[0] / 2 - 14.5*cm,
                   doc.pagesize[1] / 2 + 9.5*cm,
                   width=20, height=20)
    # canv.drawCentredString(doc.pagesize[0] / 2, doc.pagesize[1] - 15, self.report_title)

    # footer
    date_printed = 'Signatures: ............................................................'
    footer_date = canv.beginText(0, 2)
    footer_date.textLine(date_printed)
    canv.drawCentredString(doc.pagesize[0] / 2 + 8 * cm, doc.pagesize[1] - 20 * cm, date_printed)
    canv.restoreState()
