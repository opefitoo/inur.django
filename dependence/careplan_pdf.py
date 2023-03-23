import locale

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.colors import darkgray
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph, PageBreak, Table, TableStyle

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
                                  fontSize=14,
                                  parent=styles['Heading6'],
                                  alignment=TA_RIGHT,
                                  spaceAfter=5)
    normalstyle = ParagraphStyle('normalstyle',
                                 fontName="Helvetica",
                                 fontSize=14,
                                 parent=styles['Heading6'],
                                 alignment=TA_LEFT,
                                 spaceAfter=5)
    smallstyle = ParagraphStyle('smallstyle',
                                fontName="Helvetica",
                                fontSize=12,
                                parent=styles['Normal'],
                                alignment=TA_LEFT,
                                spaceAfter=0)
    smallstyle_gray = ParagraphStyle('smallstyle_gray',
                                     fontName="Helvetica",
                                     textColor=darkgray,
                                     fontSize=10,
                                     parent=styles['Normal'],
                                     alignment=TA_LEFT,
                                     spaceAfter=0)
    elements.append(Paragraph(
        u"Patient: %s" % care_plan.patient,
        patientstyle))
    elements.append(Paragraph(
        u"Matricule: %s" % care_plan.patient.code_sn,
        patientstyle))
    titlist = ParagraphStyle('titlist',
                             fontName="Helvetica-Bold",
                             fontSize=18,
                             parent=styles['Heading2'],
                             alignment=TA_CENTER,
                             spaceAfter=14)
    elements.append(Paragraph(
        u"Plan de Soins Détaillé Conclu avec le Patient",
        titlist))
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    if care_plan.plan_decision_date:
        elements.append(Paragraph(
            u"Plan N°: %s - Dès le: %s (décision du %s)"
            % (care_plan.plan_number,
               care_plan.plan_start_date.strftime("%d %B %Y"),
               care_plan.plan_decision_date.strftime("%d %B %Y")),
            normalstyle))
    else:
        elements.append(Paragraph(
            u"Plan N°: %s - Dès le: %s" % (care_plan.plan_number, care_plan.plan_start_date.strftime("%d %B %Y")),
            normalstyle))

    if care_plan.replace_plan_number:
        elements.append(Paragraph(
            u"En remplacement du plan N°: %s" % care_plan.replace_plan_number,
            normalstyle))
    data = [(Paragraph("<strong>Périodicité</strong>", smallstyle),
             Paragraph("<strong>Actions à prévoir</strong>", smallstyle))]
    i = 0
    for detail in CarePlanDetail.objects.filter(care_plan_to_master_id=care_plan.pk).order_by("id").all():
        i += 1
        data.append(
            (Paragraph(u"%s vers %s" % (','.join(str(o).upper() for o in detail.params_occurrence.all()), detail.time_start.strftime("%H:%M")), smallstyle),
             Paragraph(str(detail.care_actions).replace('\n', '<br />\n'), smallstyle)))

    elements.append(Spacer(1, 18))
    table = Table(data, [6 * cm, 22 * cm], repeatRows=1)
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))
    elements.append(table)
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("MÀJ %s" % care_plan.updated_on.strftime("%d %B %Y %H:%M"), smallstyle_gray))
    return elements


Title = "Hello world"
pageinfo = "platypus example"


def myFirstPage(canv, doc):
    canv.saveState()
    canv.setPageSize(doc.pagesize)
    canv.setTitle(doc.title)

    # # header
    canv.drawImage(BASE_DIR + "/static/patientanamnesis/images/logo.png", doc.pagesize[0] / 2 - 13.5 * cm,
                   doc.pagesize[1] / 2 + 8.5 * cm,
                   width=37*1.8, height=15*1.8, mask='auto')

    # footer
    signature = 'Signatures: ............................................................'
    # footer_date = canv.beginText(0, 2)
    # footer_date.textLine(signature)
    canv.drawCentredString(doc.pagesize[0] / 2 + 8 * cm, doc.pagesize[1] - 20 * cm, signature)
    canv.restoreState()
