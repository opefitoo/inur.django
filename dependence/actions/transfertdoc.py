import docx
from django.http import HttpResponse
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor


def add_page_number(paragraph):
    # Create a PAGE field
    fldChar1 = OxmlElement('w:fldChar')  # Create the <w:fldChar> element
    fldChar1.set(qn('w:fldCharType'), 'begin')  # Set field type to begin

    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = "PAGE"

    fldChar2 = OxmlElement('w:fldChar')  # Create the <w:fldChar> element
    fldChar2.set(qn('w:fldCharType'), 'end')  # Set field type to end

    paragraph._element.append(fldChar1)
    paragraph._element.append(instrText)
    paragraph._element.append(fldChar2)


def add_field(paragraph, field_type):
    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    run._r.append(fldChar1)

    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = field_type
    run._r.append(instrText)

    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    run._r.append(fldChar2)

    fldChar3 = OxmlElement('w:t')
    fldChar3.text = "1"  # This is a placeholder, Word will replace it
    run._r.append(fldChar3)

    fldChar4 = OxmlElement('w:fldChar')
    fldChar4.set(qn('w:fldCharType'), 'end')
    run._r.append(fldChar4)



def generate_transfer_document(patientAnamnesis):
    # Create a new Document
    doc = Document()

    # Add logo in every page (header)
    section = doc.sections[0]
    header = section.header
    paragraph = header.paragraphs[0]
    run = paragraph.add_run()
    paragraph.alignment = docx.enum.text.WD_PARAGRAPH_ALIGNMENT.RIGHT
    run.add_picture('invoices/static/images/Logo_SUR_quadri_transparent_pour_copas.png', width=docx.shared.Inches(0.75))

    # Create the footer with a table
    footer = section.footer
    table = footer.add_table(rows=1, cols=2, width=docx.shared.Inches(6.5))
    table.cell(0, 0).width = docx.shared.Inches(5.5)
    table.cell(0, 1).width = docx.shared.Inches(1.0)

    # Add text to the left side of the footer
    left_cell = table.cell(0, 0).paragraphs[0]
    run = left_cell.add_run(
        'Fiche de transfert de %s %s (%s)' % (patientAnamnesis.patient.first_name, patientAnamnesis.patient.name,
                                              patientAnamnesis.updated_on.strftime('%d-%m-%Y %H:%M')))
    run.italic = True
    run.font.size = Pt(9)  # Smaller font size
    run.font.color.rgb = RGBColor(128, 128, 128)  # Gray color (RGB 128, 128, 128)

    table.cell(0, 0).vertical_alignment = docx.enum.table.WD_ALIGN_VERTICAL.BOTTOM

    # Add page numbers to the right side of the footer
    right_cell = table.cell(0, 1).paragraphs[0]
    right_cell.alignment = docx.enum.text.WD_PARAGRAPH_ALIGNMENT.RIGHT
    run = right_cell.add_run('Page ')
    add_field(right_cell, 'PAGE')
    run = right_cell.add_run(' sur ')
    add_field(right_cell, 'NUMPAGES')

    table.cell(0, 1).vertical_alignment = docx.enum.table.WD_ALIGN_VERTICAL.BOTTOM

    # Add a line to separate the header from the content
    paragraph = doc.add_paragraph()
    paragraph.add_run().add_break(docx.enum.text.WD_BREAK.LINE)

    # Add a title
    doc.add_heading('FICHE DE TRANSFERT',
                    level=0)

    # Add the base data section
    doc.add_heading('Données de base', level=1)
    doc.add_paragraph('Nom Prénom : %s %s' % (patientAnamnesis.patient.first_name, patientAnamnesis.patient.name))
    doc.add_paragraph('Adresse: %s' % patientAnamnesis.patient.get_full_address_date_based())
    doc.add_paragraph('Matricule : %s' % patientAnamnesis.patient.code_sn)
    doc.add_paragraph('Tél: %s' % patientAnamnesis.patient.phone_number)
    doc.add_paragraph('Caisse(s) de maladie : %s' % patientAnamnesis.patient.get_caisse_maladie_display())
    doc.add_paragraph('Etat civil : %s' % patientAnamnesis.civil_status)
    # if is_under_dependence_insurance is True display "OUI" else "NON"
    doc.add_paragraph(
        'Assurance dépendance : %s' % ('OUI' if patientAnamnesis.patient.is_under_dependence_insurance else 'NON'))
    doc.add_paragraph('Degré de dépendance : %s ' % patientAnamnesis.dependance_insurance_level)
    doc.add_paragraph('Nationalité : %s ' % patientAnamnesis.nationality)
    doc.add_paragraph('Langue(s) parlée(s): %s' % patientAnamnesis.spoken_languages)
    doc.add_paragraph('Langue(s) comprise(s) : %s' % patientAnamnesis.spoken_languages)
    doc.add_paragraph('Régime de protection juridique: %s ' % patientAnamnesis.legal_protection_regimes)

    # Add the contact persons section
    doc.add_heading('Personne(s) de contact', level=1)
    contact_string_list = patientAnamnesis.get_list_of_beautiful_string_for_contact_persons()
    for contact_string in contact_string_list:
        doc.add_paragraph(contact_string)

    # Add doctor and medical sections
    doc.add_heading('Médecin(s) traitant(s) :', level=1)
    if patientAnamnesis.get_list_of_beautiful_string_for_main_assigned_physicians():
        for doctor in patientAnamnesis.get_list_of_beautiful_string_for_main_assigned_physicians():
            doc.add_paragraph(doctor)
    else:
        doc.add_paragraph('Aucun médecin traitant assigné')
    # Other doctors section
    if patientAnamnesis.get_list_of_beautiful_string_for_other_assigned_physicians():
        doc.add_heading('Autre(s) médecin(s) :', level=1)
        for doctor in patientAnamnesis.get_list_of_beautiful_string_for_other_assigned_physicians():
            doc.add_paragraph(doctor)

    # Add medical data
    doc.add_heading('Données médicales', level=1)
    doc.add_paragraph('Pathologies')
    doc.add_paragraph(patientAnamnesis.pathologies)

    doc.add_paragraph('Antécédents')
    doc.add_paragraph(patientAnamnesis.medical_background)

    # Add treatment
    doc.add_heading('Traitement', level=1)
    doc.add_paragraph(patientAnamnesis.treatments)

    # Add allergies
    doc.add_heading('Allergies', level=1)
    doc.add_paragraph(patientAnamnesis.allergies)

    # Add the rest of the sections similarly...

    # Save the document to a temporary in-memory buffer
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = 'attachment; filename="Fiche_Transfert_%s_%s_du_%s.docx"' % (
        patientAnamnesis.patient.first_name, patientAnamnesis.patient.name,
        patientAnamnesis.updated_on.strftime('%d-%m-%Y'))

    doc.save(response)
    return response
