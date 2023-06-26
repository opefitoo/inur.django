import lxml.etree as ElementTree
import pandas as pd
import xmlschema
from constance import config


def generate_invoice_file(instance):
    # generate xml
    # Load the XSD schema file
    xsd_schema = xmlschema.XMLSchema('dependence/xsd/ad-fichierfacturation-505.xsd')
    # create element tree object
    root = ElementTree.Element("decompteFacturation")
    # create sub element Type
    typeDecompte = ElementTree.SubElement(root, "typeDecompte")
    # create sub element CadreLegal
    CadreLegal = ElementTree.SubElement(typeDecompte, "CadreLegal")
    CadreLegal.text = "ASD"
    # create sub element Layout
    Layout = ElementTree.SubElement(typeDecompte, "Layout")
    Layout.text = "1"
    # create sub element Type
    Type = ElementTree.SubElement(typeDecompte, "Type")
    Type.text = "FAC"
    # create sub element Organisme
    entete = ElementTree.SubElement(root, "entete")
    identifiantFacturier = ElementTree.SubElement(entete, "identifiantFacturier")
    identifiantFacturier.text = config.CODE_PRESTATAIRE
    # create sub element Organisme
    organisme = ElementTree.SubElement(entete, "organisme")
    organisme.text = "19"
    dateEnvoi = ElementTree.SubElement(entete, "dateEnvoi")
    dateEnvoi.text = instance.invoice_sent_date.strftime("%Y-%m-%d")
    referenceFichierFacturation = ElementTree.SubElement(entete, "referenceFichierFacturation")
    referenceFichierFacturation.text = "19" + instance.invoice_sent_date.strftime("%Y%m%d")
    periodeDecompte = ElementTree.SubElement(entete, "periodeDecompte")
    exercice = ElementTree.SubElement(periodeDecompte, "exercice")
    exercice.text = str(instance.year)
    mois = ElementTree.SubElement(periodeDecompte, "mois")
    mois.text = str(instance.month)
    demandeDecompte = ElementTree.SubElement(entete, "demandeDecompte")
    nombre = ElementTree.SubElement(demandeDecompte, "nombre")
    devise = ElementTree.SubElement(demandeDecompte, "devise")
    devise.text = "EUR"
    montantBrut = ElementTree.SubElement(demandeDecompte, "montantBrut")
    montantBrut.text = "0"
    montantNet = ElementTree.SubElement(demandeDecompte, "montantNet")
    montantNet.text = "0"
    # passages is all the days between invoice_start_period to invoice_end_period
    date_ranges = pd.date_range(instance.invoice_start_period, instance.invoice_end_period, freq='D')
    print(date_ranges)
    # invoice_items is all the invoice items for the invoice
    i = 0
    facture = ElementTree.SubElement(root, "facture")
    referenceFacture = ElementTree.SubElement(facture, "referenceFacture")
    referenceFacture.text = "19" + str(instance.id)
    numeroOrdreFacture = ElementTree.SubElement(facture, "numeroOrdreFacture")
    numeroOrdreFacture.text = str(i)
    identifiantPersonneProtegee = ElementTree.SubElement(facture, "identifiantPersonneProtegee")
    identifiantPersonneProtegee.text = instance.patient.code_sn.strip()
    dateEtablissementFacture = ElementTree.SubElement(facture, "dateEtablissementFacture")
    dateEtablissementFacture.text = instance.invoice_sent_date.strftime("%Y-%m-%d")
    for invoice_item in instance.invoice.all():
        prestation = ElementTree.SubElement(facture, "prestation")
        referencePrestation = ElementTree.SubElement(prestation, "referencePrestation")
        referencePrestation.text = str(invoice_item.id)
        numeroOrdrePrestation = ElementTree.SubElement(prestation, "numeroOrdrePrestation")
        numeroOrdrePrestation.text = str(i)
        acte = ElementTree.SubElement(facture, "acte")
        codeTarif = ElementTree.SubElement(acte, "codeTarif")
        codeTarif.text = invoice_item.long_term_care_item.code
        periodePrestation = ElementTree.SubElement(prestation, "periodePrestation")
        periodePrestation.text = invoice_item.item_date.strftime("%Y-%m-%d")
        demandePrestation = ElementTree.SubElement(prestation, "demandePrestation")
        nombre = ElementTree.SubElement(demandePrestation, "nombre")
        nombre.text = "1"
        devise = ElementTree.SubElement(demandePrestation, "devise")
        devise.text = "EUR"
        montantBrut = ElementTree.SubElement(demandePrestation, "montantBrut")
        montantBrut.text = str(invoice_item.long_term_care_item.price)
        montantNet = ElementTree.SubElement(demandePrestation, "montantNet")
        montantNet.text = str(invoice_item.long_term_care_item.price)
        i += 1
    mydata = ElementTree.tostring(root, xml_declaration=True, encoding='UTF-8')
    if xsd_schema.is_valid(mydata):
        print("The XML instance is valid!")
    else:
        xsd_schema.validate(mydata)
    return mydata
