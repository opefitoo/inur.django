import calendar
import hashlib
import io
import locale
import os
import traceback
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import timedelta, date
from decimal import Decimal
from xml.etree import ElementTree

import fitz
import xmlschema
from constance import config
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q, F, CharField
from django.db.models.functions import Concat, ExtractYear, ExtractMonth
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from dependence.detailedcareplan import get_summaries_between_two_dates, MedicalCareSummaryPerPatientDetail
from dependence.longtermcareitem import LongTermCareItem, LongTermPackage
from invoices.employee import Employee
from invoices.models import Patient, Hospitalization, SubContractor, PatientSubContractorRelationship
from invoices.modelspackage import InvoicingDetails
from invoices.notifications import notify_system_via_google_webhook


def long_term_care_monthly_statement_file_path(instance, filename):
    # Ainsi le nom des fichiers commence toujours :
    # - par la lettre ‘D’ pour les fichiers de l’assurance dépendance
    # − puis par le code prestataire à 8 positions
    # − puis par l’année de décompte sur 4 positions
    # − puis par le mois de décompte ou numéro d’envoi sur 2 positions
    # − puis par le caractère ‘_’
    # − puis par un identifiant convention à 3 positions qui définit une convention dans le cadre
    # de laquelle la facturation est demandée.
    # − puis par le caractère ‘_’
    # − puis par le type fichier
    # − puis par le caractère ‘_’
    # − puis par le numéro de layout
    # − puis par le caractère ‘_’
    # − puis par une référence.
    # − puis par le caractère ‘_’
    # Illustration schématique :
    # [F/D][Code prestataire][Année][Envoi]_[Cadre légal]_[Type Fichier]_[Numéro Layout]_[Référence]
    # format integer to display 2 digits
    month_of_count = f"{instance.month:02d}"
    year_of_count = f"{instance.year:04d}"
    _internal_reference = instance.date_of_submission.strftime("%Y%m%d")
    newfilename = f"D{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_ASD_FAC_002_{_internal_reference}{instance.id}.XML"
    path = f"long_term_invoices/{instance.year}/{instance.month}/{newfilename}"

    # Check if file exists
    counter = 1
    original_path = path
    while default_storage.exists(path):
        # If file exists, modify the filename to avoid overwriting
        path_parts = os.path.splitext(original_path)  # Separate filename and extension
        path = f"{path_parts[0]}_{counter}{path_parts[1]}"  # Append counter before extension
        counter += 1

    return path


def long_term_care_monthly_statement_file_path_bis(instance, filename):
    # Ainsi le nom des fichiers commence toujours :
    # - par la lettre ‘D’ pour les fichiers de l’assurance dépendance
    # − puis par le code prestataire à 8 positions
    # − puis par l’année de décompte sur 4 positions
    # − puis par le mois de décompte ou numéro d’envoi sur 2 positions
    # − puis par le caractère ‘_’
    # − puis par un identifiant convention à 3 positions qui définit une convention dans le cadre
    # de laquelle la facturation est demandée.
    # − puis par le caractère ‘_’
    # − puis par le type fichier
    # − puis par le caractère ‘_’
    # − puis par le numéro de layout
    # − puis par le caractère ‘_’
    # − puis par une référence.
    # − puis par le caractère ‘_’
    # Illustration schématique :
    # [F/D][Code prestataire][Année][Envoi]_[Cadre légal]_[Type Fichier]_[Numéro Layout]_[Référence]
    # format integer to display 2 digits
    month_of_count = f"{instance.link_to_monthly_statement.month:02d}"
    year_of_count = f"{instance.link_to_monthly_statement.year:04d}"
    _internal_reference = instance.link_to_monthly_statement.date_of_submission.strftime("%Y%m%d")
    newfilename = f"D{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_ASD_FAC_002_{_internal_reference}{instance.id}.XML"
    path = f"long_term_invoices/{instance.link_to_monthly_statement.year}/{instance.link_to_monthly_statement.month}/{newfilename}"

    # Check if file exists
    counter = 1
    original_path = path
    while default_storage.exists(path):
        # If file exists, modify the filename to avoid overwriting
        path_parts = os.path.splitext(original_path)  # Separate filename and extension
        path = f"{path_parts[0]}_{counter}{path_parts[1]}"  # Append counter before extension
        counter += 1

    return path


def long_term_care_monthly_statement_response_file_path(instance, filename):
    return f"long_term_invoices/{instance.year}/{instance.month}/{filename}"


def long_term_care_monthly_statement_response_file_path_bis(instance, filename):
    return f"long_term_invoices/{instance.link_to_monthly_statement.year}/{instance.link_to_monthly_statement.month}/{filename}"


# décompte mensuel de factures
class LongTermCareMonthlyStatement(models.Model):
    class Meta:
        verbose_name = _("Décompte mensuel de factures")
        verbose_name_plural = _("Décomptes mensuels de factures")

    year = models.PositiveIntegerField(_('Year'))
    # invoice month
    month = models.PositiveIntegerField(_('Month'))
    generated_invoice_file = models.FileField(_('Generated Invoice File'),
                                              upload_to=long_term_care_monthly_statement_file_path,
                                              blank=True, null=True)
    force_regeneration = models.BooleanField(_('Force Regeneration'), default=False)
    # dateEnvoi
    date_of_submission = models.DateField(_('Date d\'envoi du fichier'), blank=True, null=True)
    # dateReception
    generated_invoice_file_response = models.FileField(_('Generated Invoice Response File'),
                                                       upload_to=long_term_care_monthly_statement_response_file_path,
                                                       blank=True, null=True)
    date_of_receipt = models.DateField(_('Date de réception du fichier'), blank=True, null=True)

    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def generate_invoice_pdf_from_template_from_field_forms(self, sending_to_update=None):
        pdf_path = 'dependence/pdf/ASS_DEP_TEMPL_WIT_FORMS.pdf'
        doc = fitz.open(pdf_path)
        # format date sending_to_update.date_of_sending_xml_file to french format
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        french_sending_date = sending_to_update.date_of_sending_xml_file.strftime('%d %B %Y')
        field_values = {
            'mm_aaaa': '%s / %s' % (self.month, self.year),
            'month' : '%s' % self.month,
            'invoice_count' : str(self.get_number_of_invoices),
            'invoice_lines_count': str(self.total_number_of_lines()),
            'french_date' : french_sending_date,
            'total_amount' : self.total_price_formatted()
        }

        for page in doc:
            widgets = page.widgets()
            for widget in widgets:
                if widget.field_name in field_values:
                    widget.field_value = field_values[widget.field_name]
                    # Ensure changes are committed to the widget
                    widget.update()

        # Format the current time for the filename
        current_time_str = timezone.now().strftime("%Y%m%d%H%M%S")
        month_year = f"{self.month}_{self.year}"
        output_filename = f"dependence/pdf/out/PDF_INVOICE_{month_year}_{current_time_str}.pdf"

        # Save the modified PDF to a BytesIO object
        pdf_bytes = io.BytesIO()
        doc.save(pdf_bytes)
        pdf_bytes.seek(0)

        # Create a Django ContentFile from the BytesIO object
        pdf_file = ContentFile(pdf_bytes.read(), name=output_filename)

        # Save the file to S3
        sending_to_update.scan_of_signed_invoice = pdf_file
        sending_to_update.save()

    def generate_xml_using_xmlschema(self, sending_to_update=None):

        # Load the XSD schema file
        # go one folder up
        # Get the current script's directory
        current_directory = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the XSD file
        xsd_path = os.path.join(current_directory, 'xsd', 'ad-fichierfacturation-505.xsd')

        # Load the XSD schema
        xsd_schema = xmlschema.XMLSchema(xsd_path)
        # xsd_schema = xmlschema.XMLSchema(settings.BASE_DIR + '/dependence/xsd/ad-declaration-14.xsd')
        # create element tree object
        root = ElementTree.Element("decompteFacturation")
        # create sub element typeDecompte
        typeDecompte = ElementTree.SubElement(root, "typeDecompte")
        # create sub element cadreLegal
        cadreLegal = ElementTree.SubElement(typeDecompte, "cadreLegal")
        cadreLegal.text = "ASD"
        # create sub element layout
        layout = ElementTree.SubElement(typeDecompte, "layout")
        layout.text = "2"
        # create sub element Type
        type = ElementTree.SubElement(typeDecompte, "type")
        type.text = "FAC"

        # create sub element entete
        entete = ElementTree.SubElement(root, "entete")
        # create sub element identifiantFacturier
        identifiantFacturier = ElementTree.SubElement(entete, "identifiantFacturier")
        identifiantFacturier.text = config.CODE_PRESTATAIRE
        # create sub element organisme
        organisme = ElementTree.SubElement(entete, "organisme")
        organisme.text = "19"
        # create sub element dateEnvoi
        if sending_to_update:
            dateEnvoi = ElementTree.SubElement(entete, "dateEnvoi")
            dateEnvoi.text = sending_to_update.date_of_sending_xml_file.strftime("%Y-%m-%d")
        else:
            raise Exception("Sending to update is not implemented yet")
        # create sub element referenceFichierFacturation
        referenceFichierFacturation = ElementTree.SubElement(entete, "referenceFichierFacturation")
        referenceFichierFacturation.text = str(self.id)
        # create sub element periodeDecompte
        periodeDecompte = ElementTree.SubElement(entete, "periodeDecompte")
        # create sub element exercice
        exercice = ElementTree.SubElement(periodeDecompte, "exercice")
        exercice.text = str(self.year)
        # create sub element mois
        mois = ElementTree.SubElement(periodeDecompte, "mois")
        mois.text = str(self.get_month_in_2_digits)
        # create sub element demandeDecompte
        demandeDecompte = ElementTree.SubElement(entete, "demandeDecompte")
        # create sub element nombre
        nombre = ElementTree.SubElement(demandeDecompte, "nombre")
        # set number of invoices per patient
        invoices = LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all()
        nombre.text = str(self.get_number_of_invoices)
        # create sub element devise
        devise = ElementTree.SubElement(demandeDecompte, "devise")
        devise.text = "EUR"
        # create sub element montantBrut
        montantBrut = ElementTree.SubElement(demandeDecompte, "montantBrut")
        montantBrut.text = str(self.calculate_total_price())
        # create sub element montantNet
        montantNet = ElementTree.SubElement(demandeDecompte, "montantNet")
        montantNet.text = str(self.calculate_total_price())
        # loop through all LongTermCareInvoiceFile
        _counter = 0
        invoice_count = 0
        for invoice in invoices:
            if invoice.calculate_price() == 0:
                # skip invoice already paid
                continue
            invoice_count += 1
            # create sub element facture
            facture = ElementTree.SubElement(root, "facture")
            print(invoice)
            # create sub element referenceFacture
            referenceFacture = ElementTree.SubElement(facture, "referenceFacture")
            # set referenceFacture is year _ month _  invoice.id
            referenceFacture.text = str(self.year) + str(self.month) + str(invoice.id)
            # create sub element identifiantPersonneProtegee
            identifiantPersonneProtegee = ElementTree.SubElement(facture, "identifiantPersonneProtegee")
            identifiantPersonneProtegee.text = invoice.patient.code_sn
            # create sub element dateEtablissementFacture
            if sending_to_update:
                dateEtablissementFacture = ElementTree.SubElement(facture, "dateEtablissementFacture")
                dateEtablissementFacture.text = sending_to_update.date_of_sending_xml_file.strftime("%Y-%m-%d")
            else:
                raise Exception("Sending to update is not implemented yet")
            # loop through all LongTermCareInvoiceLine
            for item in LongTermCareInvoiceItem.objects.filter(invoice=invoice).all().all():
                if item.paid:
                    # skip invoice line already paid
                    continue
                _counter += 1
                # create sub element prestation
                prestation = ElementTree.SubElement(facture, "prestation")
                # create sub element codePrestation
                referencePrestation = ElementTree.SubElement(prestation, "referencePrestation")
                referencePrestation.text = str(invoice.id) + str(_counter) + str(item.id)
                # create sub element acte
                acte = ElementTree.SubElement(prestation, "acte")
                # create sub element codeTarif
                codeTarif = ElementTree.SubElement(acte, "codeTarif")
                codeTarif.text = item.long_term_care_package.code
                # create sub element periodePrestation
                periodePrestation = ElementTree.SubElement(prestation, "periodePrestation")
                # create sub element dateDebut
                dateDebut = ElementTree.SubElement(periodePrestation, "dateDebut")
                dateDebut.text = item.care_date.strftime("%Y-%m-%d")
                # create sub element dateFin
                dateFin = ElementTree.SubElement(periodePrestation, "dateFin")
                dateFin.text = item.care_date.strftime("%Y-%m-%d")
                # create sub element demandePrestation
                demandePrestation = ElementTree.SubElement(prestation, "demandePrestation")
                # create sub element nombre
                nombre = ElementTree.SubElement(demandePrestation, "nombre")
                nombre.text = str(int(item.quantity))
                # create sub element devise
                devise = ElementTree.SubElement(demandePrestation, "devise")
                devise.text = "EUR"
                # create sub element montantBrut
                montantBrut = ElementTree.SubElement(demandePrestation, "montantBrut")
                montantBrut.text = str(item.calculate_price())
                # create sub element montantNet
                montantNet = ElementTree.SubElement(demandePrestation, "montantNet")
                montantNet.text = str(item.calculate_price())
                # create sub element identifiantExecutant
                identifiantExecutant = ElementTree.SubElement(prestation, "identifiantExecutant")
                if item.subcontractor and item.long_term_care_package.code == "AMDGG":
                    if item.subcontractor.provider_code is None:
                        raise   Exception(f"Provider code is not set for {item.subcontractor}")
                    identifiantExecutant.text = item.subcontractor.provider_code
                else:
                    identifiantExecutant.text = config.CODE_PRESTATAIRE

            for line in LongTermCareInvoiceLine.objects.filter(invoice=invoice).all().all():
                if line.paid:
                    # skip invoice line already paid
                    continue
                for line_per_day in line.get_line_item_per_each_day_of_period():
                    _counter += 1
                    # create sub element prestation
                    prestation = ElementTree.SubElement(facture, "prestation")
                    # create sub element codePrestation
                    referencePrestation = ElementTree.SubElement(prestation, "referencePrestation")
                    referencePrestation.text = str(invoice.id) + str(_counter)
                    # create sub element acte
                    acte = ElementTree.SubElement(prestation, "acte")
                    # create sub element codeTarif
                    codeTarif = ElementTree.SubElement(acte, "codeTarif")
                    codeTarif.text = line.long_term_care_package.code
                    # create sub element periodePrestation
                    periodePrestation = ElementTree.SubElement(prestation, "periodePrestation")
                    # create sub element dateDebut
                    dateDebut = ElementTree.SubElement(periodePrestation, "dateDebut")
                    # dateDebut.text = line.start_period.strftime("%Y-%m-%d")
                    dateDebut.text = line_per_day.care_date.strftime("%Y-%m-%d")
                    # create sub element dateFin
                    # dateFin = ElementTree.SubElement(periodePrestation, "dateFin")
                    # dateFin.text = line.end_period.strftime("%Y-%m-%d")

                    # create sub element demandePrestation
                    demandePrestation = ElementTree.SubElement(prestation, "demandePrestation")
                    # create sub element nombre
                    nombre = ElementTree.SubElement(demandePrestation, "nombre")
                    nombre.text = "1"
                    # create sub element devise
                    devise = ElementTree.SubElement(demandePrestation, "devise")
                    devise.text = "EUR"
                    # create sub element montantBrut
                    montantBrut = ElementTree.SubElement(demandePrestation, "montantBrut")
                    montantBrut.text = str(line.calculate_price_per_day())
                    # create sub element montantNet
                    montantNet = ElementTree.SubElement(demandePrestation, "montantNet")
                    montantNet.text = str(line.calculate_price_per_day())
                    # create sub element identifiantExecutant
                    identifiantExecutant = ElementTree.SubElement(prestation, "identifiantExecutant")
                    identifiantExecutant.text = config.CODE_PRESTATAIRE
            # create sub element demandeFacture
            demandeFacture = ElementTree.SubElement(facture, "demandeFacture")
            # create sub element nombre
            nombre = ElementTree.SubElement(demandeFacture, "nombre")
            nombre.text = str(invoice_count)
            # create sub element devise
            devise = ElementTree.SubElement(demandeFacture, "devise")
            devise.text = "EUR"
            # create sub element montantBrut
            montantBrut = ElementTree.SubElement(demandeFacture, "montantBrut")
            montantBrut.text = str(invoice.calculate_price())
            # create sub element montantNet
            montantNet = ElementTree.SubElement(demandeFacture, "montantNet")
            montantNet.text = str(invoice.calculate_price())
        # create a new XML file with the results
        mydata = ElementTree.tostring(root, xml_declaration=True, encoding='UTF-8')
        if xsd_schema.is_valid(mydata):
            print("The XML instance is valid!")
        else:
            xsd_schema.validate(mydata)
        return mydata

    def calculate_total_price(self):
        total_price = 0
        for invoice in LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all():
            total_price += invoice.calculate_price()
        return total_price

    def total_price_formatted(self):
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')  # Unix/Linux/MacOS
        # locale.setlocale(locale.LC_ALL, 'french')  # Windows
        return locale.format_string("%.2f", self.calculate_total_price(), grouping=True, monetary=True)

    def total_number_of_lines(self):
        _total_number_of_lines = 0
        for invoice in LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all():
            _total_number_of_lines += invoice.total_number_of_lines()
        return _total_number_of_lines

    @property
    def get_invoices(self):
        return LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all().order_by('id')

    @property
    def get_month_in_french(self):
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')  # for Unix/Linux/MacOS
        # to upper case
        return calendar.month_name[self.month].upper()

    @property
    def get_provider_name(self):
        invoicing_details = InvoicingDetails.objects.filter(default_invoicing=True).first()
        if invoicing_details:
            return invoicing_details.name
        return "PLEASE FILL IN INVOICING DETAILS"

    @property
    def get_provider_address(self):
        invoicing_details = InvoicingDetails.objects.filter(default_invoicing=True).first()
        if invoicing_details:
            return invoicing_details.get_full_address
        return "PLEASE FILL IN INVOICING DETAILS"

    @property
    def get_provider_code(self):
        invoicing_details = InvoicingDetails.objects.filter(default_invoicing=True).first()
        if invoicing_details:
            return invoicing_details.provider_code
        return "PLEASE FILL IN INVOICING DETAILS"

    @property
    def get_number_of_invoices(self):
        all_invoices = LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all()
        for inv in all_invoices:
            if inv.calculate_price() == 0:
                all_invoices = all_invoices.exclude(id=inv.id)
        return all_invoices.count()

    @property
    def get_month_in_2_digits(self):
        return str(self.month).zfill(2)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.force_regeneration and not self.date_of_submission:
            raise ValidationError("Please fill in the date of submission if you want to generate the invoice file")
        self.force_regeneration = False

    def __str__(self):
        return f"{self.year} - {self.month}"


def create_and_save_invoice_file(sender, instance, **kwargs):
    if not instance.force_regeneration:
        return
    message = f"Le fichier de factures mensuel {instance} a été généré avec succès. Date heure : {timezone.now()}"
    if instance.force_regeneration:
        try:
            xml_str = instance.generate_xml_using_xmlschema()
            # save the file
            xml_file = ContentFile(xml_str, name=f"{instance.year}_{instance.month}.xml")
            instance.generated_invoice_file = xml_file
        except Exception as e:
            message = f"Le fichier de factures mensuel {instance} n'a pas pu être généré. Erreur : {e}. Date heure : {timezone.now()}"
            message += f" Détails de l'erreur : {traceback.format_exc()}"
            notify_system_via_google_webhook(message)
            print(e)
        finally:
            notify_system_via_google_webhook(message)
            instance.force_regeneration = False


@receiver(pre_save, sender=LongTermCareMonthlyStatement,
          dispatch_uid="generate_xml_monthly_statement_and_notify_via_chat")
def create_and_save_invoice_file(sender, instance, **kwargs):
    if not instance.force_regeneration:
        return
    message = f"Le fichier de factures mensuel {instance} a été généré avec succès. Date heure : {timezone.now()}"
    sending_files = LongTermCareMonthlyStatementSending.objects.filter(link_to_monthly_statement=instance,
                                                                       received_invoice_file_response=None).all()
    if sending_files.count() > 1:
        raise ValidationError(
            "Il y a plus d'un fichier de facture mensuel envoyé. Veuillez supprimer les fichiers en trop.")
    if sending_files.count() == 1:
        sending_to_update = sending_files.first()
    elif sending_files.count() == 0:
        sending_to_update = LongTermCareMonthlyStatementSending.objects.create(link_to_monthly_statement=instance)
    if instance.force_regeneration:
        try:
            if sending_to_update.date_of_sending_xml_file is None:
                sending_to_update.date_of_sending_xml_file = timezone.now()
            xml_str = instance.generate_xml_using_xmlschema(sending_to_update=sending_to_update)
            # update a pdf file with invoice data
            instance.generate_invoice_pdf_from_template_from_field_forms(sending_to_update=sending_to_update)
            # save the file
            xml_file = ContentFile(xml_str, name=f"{instance.year}_{instance.month}.xml")
            sending_to_update.xml_invoice_file = xml_file
            sending_to_update.link_to_monthly_statement = instance
            sending_to_update.save()
        except Exception as e:
            message = f"Le fichier de factures mensuel {instance} n'a pas pu être généré. Erreur : {e}. Date heure : {timezone.now()}"
            message += f" Détails de l'erreur : {traceback.format_exc()}"
            notify_system_via_google_webhook(message)
            print(e)
        finally:
            notify_system_via_google_webhook(message)
            instance.force_regeneration = False


class LongTermCareMonthlyStatementSending(models.Model):
    link_to_monthly_statement = models.ForeignKey(LongTermCareMonthlyStatement, on_delete=models.CASCADE,
                                                  related_name='monthly_statement_xml_file', blank=True, null=True)
    xml_invoice_file = models.FileField(_('Generated Invoice File'),
                                        upload_to=long_term_care_monthly_statement_file_path_bis,
                                        blank=True, null=True)
    date_of_sending_xml_file = models.DateField(_('Date d\'envoi du fichier'), blank=True, null=True)
    received_invoice_file_response = models.FileField(_('Received Invoice Response File'),
                                                      upload_to=long_term_care_monthly_statement_response_file_path_bis,
                                                      blank=True, null=True)
    scan_of_signed_invoice = models.FileField(_('Scan of Signed Invoice'),
                                              upload_to='long_term_invoices/signed/',
                                              blank=True, null=True)
    date_of_receipt_of_response_file = models.DateField(_('Date de réception du fichier de retour'), blank=True,
                                                        null=True)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        return f"{self.link_to_monthly_statement} - date of receipt of response file : {self.date_of_receipt_of_response_file}"


def normalize_and_hash_xml(xml_file):
    # Parse the XML
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Normalize: Implement normalization logic as per your requirements
    normalized_xml_str = ET.tostring(root, encoding='utf-8', method='xml')

    # Compute hash
    sha256 = hashlib.sha256()
    sha256.update(normalized_xml_str)
    return sha256.hexdigest()

def has_no_anomalie_prestation(element):
    return not element.find('.//anomaliePrestation') is not None

def detect_anomalies(instance):
    # Parse the XML file
    tree = ET.parse(instance.received_invoice_file_response)
    root = tree.getroot()

    # Navigate to the 'montantNet' element and extract its text content
    montant_net_element = root.find('./entete/paiementGroupeTraitement/montantNet')
    montant_brut_element = root.find('./entete/paiementGroupeTraitement/montantBrut')
    if montant_brut_element is None or montant_net_element is None:
        raise ValueError("Could not find montantBrut or montantNet in the XML.")

    montant_brut = float(montant_brut_element.text)
    montant_net = float(montant_net_element.text)

    # Compare montantBrut and montantNet
    if montant_brut != montant_net:
        print(f"Warning: montantBrut ({montant_brut}) and montantNet ({montant_net}) are not equal.")

        # parse the xml sent to find the invoice
        # Parse the XML file
        invoice_tree = ET.parse(instance.xml_invoice_file)
        invoice_root = invoice_tree.getroot()

        # Extract facture elements with anomalies
        anomalies = []
        for facture in root.findall('.//facture'):
            reference_facture = facture.find('./referenceFacture').text if facture.find(
                './referenceFacture') is not None else "Unknown"
            anomalie = facture.find('./anomalieFacture')
            items = LongTermCareInvoiceFile.objects.annotate(
                invoice_reference_filter=Concat(
                    ExtractYear('invoice_start_period'),
                    ExtractMonth('invoice_start_period'),
                    F('id'),
                    output_field=CharField()
                )
            )
            if anomalie is not None:
                # find prestation without anomalies
                # Manually filter the prestations
                prestations_without_anomalies = [prestation for prestation in facture.findall('.//prestation') if
                                                 has_no_anomalie_prestation(prestation)]
                invoice_in_error = items.filter(invoice_reference_filter=reference_facture).get()
                for prestation in prestations_without_anomalies:
                    invoiced_prestation = invoice_root.find('.//facture/prestation/[referencePrestation="{}"]'.format(
                        prestation.find('referencePrestation').text))
                    date_prestation_text = invoiced_prestation.find('periodePrestation/dateDebut').text
                    date_prestation = date.fromisoformat(date_prestation_text)
                    invoiced_code_acte = invoiced_prestation.find('acte/codeTarif').text
                    reference_prestation = prestation.find('referencePrestation').text
                    if len(LongTermCareInvoiceLine.objects.filter(invoice=invoice_in_error).filter(long_term_care_package__code=invoiced_code_acte)) == 1:
                        LongTermCareInvoiceLine.objects.filter(invoice=invoice_in_error).filter(
                            long_term_care_package__code=invoiced_code_acte).update(paid=True,
                                                                                    refused_by_insurance=False,
                                                                                    comment="")
                    else:
                        LongTermCareInvoiceItem.objects.filter(invoice=invoice_in_error).filter(
                            long_term_care_package__code=invoiced_code_acte).filter(care_date=date_prestation).update(paid=True,
                                                                                                                      refused_by_insurance=False,
                                                                                                                      comment="")
                code = anomalie.find('./code').text if anomalie.find('./code') is not None else "Unknown"
                motif = anomalie.find('./motif').text if anomalie.find('./motif') is not None else "Unknown"
                error_messages = []
                # Find all 'prestation' elements with 'anomaliePrestation' child within the current 'facture'
                prestations_with_anomalies = facture.findall('.//prestation[anomaliePrestation]')
                error_messages.append(f"Facture {reference_facture} has anomaly {code} - {motif}")
                for prestation in prestations_with_anomalies:
                    # find the invoiced prestation from the invoice file
                    invoiced_prestation = invoice_root.find('.//facture/prestation/[referencePrestation="{}"]'.format(
                        prestation.find('referencePrestation').text))
                    date_prestation_text = invoiced_prestation.find('periodePrestation/dateDebut').text
                    date_prestation = date.fromisoformat(date_prestation_text)
                    invoiced_code_acte = invoiced_prestation.find('acte/codeTarif').text
                    reference_prestation = prestation.find('referencePrestation').text
                    anomalies = prestation.findall('anomaliePrestation')
                    anomlies_text = ""
                    for anomalie in anomalies:
                        anomalie_type = anomalie.find('type').text
                        anomalie_code = anomalie.find('code').text
                        anomalie_motif = anomalie.find('motif').text
                        anomlies_text += f"Type: {anomalie_type} - Code: {anomalie_code} - Motif: {anomalie_motif}"
                    if len(LongTermCareInvoiceLine.objects.filter(invoice=invoice_in_error).filter(long_term_care_package__code=invoiced_code_acte)) == 1:
                        LongTermCareInvoiceLine.objects.filter(invoice=invoice_in_error).filter(
                            long_term_care_package__code=invoiced_code_acte).update(paid=False,
                                                                                    refused_by_insurance=True,
                                                                                    comment=anomlies_text)
                    else:
                        LongTermCareInvoiceItem.objects.filter(invoice=invoice_in_error).filter(
                            long_term_care_package__code=invoiced_code_acte).filter(care_date=date_prestation).update(paid=False,
                                                                                                                      refused_by_insurance=True,
                                                                                                                      comment=anomlies_text)
                    code_acte_paye = prestation.find('codeActePaye').text
                    anomalie = prestation.find('anomaliePrestation')
                    anomalie_type = anomalie.find('type').text
                    anomalie_code = anomalie.find('code').text
                    anomalie_motif = anomalie.find('motif').text
                    # prestation reference looks like "%s%s%s" % (self.invoice.id, self.long_term_care_package.id, date_of_line_str) extract long_term_care_package.id knowing that invoice.id is invoice_in_error.id
                    long_term_care_package_id = reference_prestation[len(str(invoice_in_error.id)):-10]
                    print(long_term_care_package_id)
                    long_term_care_package = LongTermPackage.objects.get(code=code_acte_paye)

                    # Display the extracted information
                    print(f"  - Prestation Reference: {reference_prestation}")
                    print(f"    Anomalie Type: {anomalie_type}")
                    print(f"    Anomalie Code: {anomalie_code}")
                    print(f"    Anomalie Motif: {anomalie_motif}")
                    error_messages.append(
                        f"reference prestation : {reference_prestation} - Error messages: {anomlies_text}")

                # generate a hash for all error_messages
                error_messages_hash = hashlib.sha256(str(error_messages).encode('utf-8')).hexdigest()
                # check if error message already exists
                if not InvoiceError.objects.filter(invoice=invoice_in_error,
                                                   statement_sending=instance).exists():
                    InvoiceError.objects.create(invoice=invoice_in_error,
                                                statement_sending=instance,
                                                error_message=error_messages)
                    print(f"Facture {invoice_in_error} has anomaly {code} - {motif}")
                else:
                    print(f"deleting error message for facture {invoice_in_error} and sending {instance}")
                    InvoiceError.objects.filter(invoice=invoice_in_error,
                                                statement_sending=instance).delete()
                anomalies.append((reference_facture, code, motif))
            else:
                print(f"Facture {reference_facture} has no anomalies")
                montant_net_facture = facture.find('./montantNet').text
                montant_brut_facture = facture.find('./montantBrut').text
                if float(montant_net_facture) == float(montant_brut_facture):
                    invoice_paid = items.filter(invoice_reference_filter=reference_facture).get()
                    # set lines and items as paid
                    LongTermCareInvoiceLine.objects.filter(invoice=invoice_paid).update(paid=True)
                    LongTermCareInvoiceItem.objects.filter(invoice=invoice_paid).update(paid=True)
                else:
                    raise ValueError(
                        "Montant net and montant brut are not equal {montant_net_facture} {montant_brut_facture}")
        return anomalies
    else:
        print("No anomalies detected.")
        return None


@receiver(pre_save, sender=LongTermCareMonthlyStatementSending,
          dispatch_uid="generate_xml_monthly_statement_and_notify_via_chat")
def process_xml_response_file(sender, instance, **kwargs):
    # detect if received_invoice_file_response has changed
    if not instance.received_invoice_file_response:
        return
    if not instance.link_to_monthly_statement:
        return
    if instance.pk:
        stored_instance = LongTermCareMonthlyStatementSending.objects.get(pk=instance.pk)
        if stored_instance.received_invoice_file_response and normalize_and_hash_xml(
                stored_instance.received_invoice_file_response) == normalize_and_hash_xml(
            instance.received_invoice_file_response):
            print("No change in received_invoice_file_response")
            return
    # parse the xml file
    print("Processing XML file")
    print(detect_anomalies(instance))


class LongTermCareInvoiceFile(models.Model):
    link_to_monthly_statement = models.ForeignKey(LongTermCareMonthlyStatement, on_delete=models.CASCADE,
                                                  related_name='monthly_statement', blank=True, null=True)
    # invoice year is positive integer
    invoice_start_period = models.DateField(_('Invoice Start Period'), )
    invoice_end_period = models.DateField(_('Invoice End Period'), )
    # patient only under dependance_insurance
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient',
                                limit_choices_to=Q(is_under_dependence_insurance=True))
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    # must be linked to a monthly statement that is same period as invoice file
    def clean(self):
        # MedicalCareSummaryPerPatient
        if self.link_to_monthly_statement.month != self.invoice_start_period.month:
            raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
        if self.link_to_monthly_statement.year != self.invoice_start_period.year:
            raise ValidationError("L'année de la facture doit être la même que l'année du décompte mensuel")
        if self.link_to_monthly_statement.month != self.invoice_end_period.month:
            raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
        if self.link_to_monthly_statement.year != self.invoice_end_period.year:
            raise ValidationError("L'année de la facture doit être la même que l'année du décompte mensuel")

    def export_to_xero(self):
        # send invoice to xero
        # get xero tenant_id
        xero_tenant_id = get_xero_tenant_id()
        # get xero contact_id
        xero_contact_id = get_xero_contact_id(self.patient)
        # get xero account code
        xero_account_code = get_xero_account_code(self.patient)
        # get xero tracking category id

    def calculate_price(self):
        lines = LongTermCareInvoiceLine.objects.filter(invoice=self)
        total = 0
        for line in lines:
            total += line.calculate_price()
        items = LongTermCareInvoiceItem.objects.filter(invoice=self)
        for item in items:
            total += item.calculate_price()
        total_price = round(total, 2)
        return total_price

    def total_number_of_lines(self):
        _number_of_lines = 0
        for line in LongTermCareInvoiceLine.objects.filter(
                invoice=self).all():
            _number_of_lines += len(line.get_line_item_per_each_day_of_period_not_paid())
        return _number_of_lines + LongTermCareInvoiceItem.objects.filter(
            invoice=self, paid=False).count()

    @property
    def get_invoice_items(self):
        # get LongTermCareInvoiceItem linked to this invoice
        if self.id:
            return LongTermCareInvoiceItem.objects.filter(invoice=self).order_by(
                'care_date')
        return None

    @property
    def get_lines_assigned_to_subcontractor(self):
        return LongTermCareInvoiceLine.objects.filter(invoice=self).filter(subcontractor__isnull=False).all().order_by("start_period")
    @property
    def get_items_assigned_to_subcontractor(self):
        return LongTermCareInvoiceItem.objects.filter(invoice=self).filter(subcontractor__isnull=False).all().order_by("care_date")

    @property
    def get_totals_per_subcontractor(self):
        subcontractors = SubContractor.objects.all()
        totals = {}
        for subcontractor in subcontractors:
            for item in LongTermCareInvoiceItem.objects.filter(invoice=self).filter(subcontractor=subcontractor).all():
                if subcontractor not in totals:
                    totals[subcontractor] = 0
                totals[subcontractor] += item.calculate_price()
            for line in LongTermCareInvoiceLine.objects.filter(invoice=self).filter(subcontractor=subcontractor).all():
                if subcontractor not in totals:
                    totals[subcontractor] = 0
                totals[subcontractor] += line.calculate_price()
        # return a nice looking string something like For Subcontractor 1 : 1000, For Subcontractor 2 : 2000
        return ", ".join([f"Pour {subcontractor} : {total}" for subcontractor, total in totals.items()])


    @property
    def invoice_reference(self):
        return f"{self.invoice_start_period.year}{self.invoice_start_period.month}{self.id}"

    @property
    def has_errors(self):
        return InvoiceError.objects.filter(invoice=self).exists()

    def get_errors(self):
        return InvoiceError.objects.filter(invoice=self).all()

    @property
    def display_errors_as_html(self):
        anomalies_html = ""
        for error in self.get_errors():
            anomalies_html += f"<br> {error}"
            anomalies = error.error_message.split(', ')
            anomalies_html += "<ul>"
            for error_msg in anomalies:
                anomalies_html += f"<li>{error_msg}</li>"
            anomalies_html += "</ul>"
        return mark_safe(anomalies_html)

    @property
    def get_invoice_lines(self):
        # get LongTermCareInvoiceItem linked to this invoice
        if self.id:
            return LongTermCareInvoiceLine.objects.filter(invoice=self).order_by(
                'start_period')
        return None

    def get_patient_hospitalizations(self):
        return Hospitalization.objects.filter(patient=self.patient).filter(
            start_date__lte=self.invoice_end_period).filter(end_date__gte=self.invoice_start_period)

    class Meta:
        verbose_name = _("Facture assurance dépendance")
        verbose_name_plural = _("Factures assurance dépendance")

    def __str__(self):
        return "Facture assurance dépendance de {0}/{1} patient {2}".format(self.invoice_start_period,
                                                                            self.invoice_end_period,
                                                                            self.patient)

    # on save gather all events for the month and generate the invoice file


class LongTermCareActivity(models.Model):
    INVOICE_ITEM_STATUS = (
        ('DONE', _('Done')),
        ('NOT_DONE', _('Not Done')),
        ('CANCELLED', _('Cancelled')),
    )
    invoice = models.ForeignKey(LongTermCareInvoiceFile, on_delete=models.CASCADE, related_name='invoice')
    item_date = models.DateField(_('Item Date'), )
    long_term_care_item = models.ForeignKey(LongTermCareItem, on_delete=models.CASCADE,
                                            related_name='long_term_care_item')
    assigned_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assigned_employee')
    status = models.CharField(_('Status'), max_length=100, choices=INVOICE_ITEM_STATUS, default='DONE')
    notes = models.TextField(_('Notes'), blank=True, null=True)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    class Meta:
        verbose_name = _("Ligne d'activité assurance dépendance")
        verbose_name_plural = _("Lignes d'activités assurance dépendance")
        ordering = ['item_date']

    def __str__(self):
        return "Ligne de facture assurance dépendance de {0} patient {1}".format(self.item_date,
                                                                                 self.invoice.patient)


class InvoiceError(models.Model):
    invoice = models.ForeignKey(LongTermCareInvoiceFile, on_delete=models.CASCADE)
    statement_sending = models.ForeignKey(LongTermCareMonthlyStatementSending, on_delete=models.CASCADE, null=True,
                                          blank=True)
    error_message = models.TextField()
    error_message_hash = models.CharField(max_length=255, blank=True, null=True)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        return f"Error for invoice {self.invoice}"


class LongTermCareInvoiceItem(models.Model):
    invoice = models.ForeignKey(LongTermCareInvoiceFile, on_delete=models.CASCADE, related_name='invoice_item')
    care_date = models.DateField(_('Date Début période'), )
    long_term_care_package = models.ForeignKey(LongTermPackage, on_delete=models.CASCADE,
                                               related_name='from_item_to_long_term_care_package')
    quantity = models.FloatField(_('Quantité'), default=1)
    paid = models.BooleanField(_('Paid'), default=False)
    refused_by_insurance = models.BooleanField(_('Refused by insurance'), default=False)
    comment = models.CharField(_('Comment'), max_length=500, blank=True, null=True)
    xml_invoice_reference = models.CharField(_('Référence de facturation'), max_length=255, blank=True, null=True)
    subcontractor = models.ForeignKey(
        SubContractor,
        on_delete=models.SET_NULL,
        related_name='long_term_invoice_items',
        null=True,
        blank=True
    )
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        return "Item de facture assurance dépendance de {0} patient {1}".format(self.care_date,
                                                                                self.invoice.patient)

    class Meta:
        verbose_name = _("Item facture assurance dépendance")
        verbose_name_plural = _("Item de facture assurance dépendance")

    def calculate_price(self, take_paid_or_refused_by_insurance_into_account=True):
        if take_paid_or_refused_by_insurance_into_account and (self.paid or self.refused_by_insurance):
            return 0
        else:
            if self.subcontractor:
                # - billing_retrocession % of price
                return round(self.long_term_care_package.price_per_year_month(year=self.care_date.year,
                                                                        month=self.care_date.month) * Decimal(str(self.quantity)) * (
                                1 - self.subcontractor.billing_retrocession / 100), 2)

            if self.long_term_care_package.package:
                raise ValidationError("Item seulement pour un non forfait (package doit etre false)")
            else:
                # price for specific care_date
                return self.long_term_care_package.price_per_year_month(year=self.care_date.year,
                                                                        month=self.care_date.month) * Decimal(str(self.quantity))
    def amount_due(self):
        return self.calculate_price(take_paid_or_refused_by_insurance_into_account=False)

    def calculate_unit_price(self):
        if self.subcontractor:
            # - billing_retrocession % of price
            return round(self.long_term_care_package.price_per_year_month(year=self.care_date.year,
                                                                    month=self.care_date.month) * (
                            1 - self.subcontractor.billing_retrocession / 100), 2)
        if self.long_term_care_package.package:
            raise ValidationError("Item seulement pour un non forfait (package doit etre false)")
        else:
            # price for specific care_date
            return self.long_term_care_package.price_per_year_month(year=self.care_date.year,
                                                                    month=self.care_date.month)

    def clean(self):
        self.validate_item_dates_are_in_same_month_year_as_invoice()
        self.validate_lines_are_made_by_correct_sub_contractor()

    def validate_item_dates_are_in_same_month_year_as_invoice(self):
        if self.invoice.invoice_start_period.year != self.care_date.year or self.invoice.invoice_start_period.month != self.care_date.month:
            raise ValidationError("La date de l'item doit être dans le même mois et année que la facture")

    def validate_lines_are_made_by_correct_sub_contractor(self):
        if self.subcontractor:
            if not PatientSubContractorRelationship.objects.filter(patient=self.invoice.patient,
                                                                   subcontractor=self.subcontractor).exists():
                # list of all sub contractors for this patient
                sub_contractors = PatientSubContractorRelationship.objects.filter(patient=self.invoice.patient)
                raise ValidationError(
                    "Le sous-traitant de la ligne doit être le même que celui du patient (%s)" % sub_contractors)


@dataclass
class LongTermCareInvoiceLinePerDay:
    care_reference: str
    care_date: date
    care_package: LongTermPackage


class LongTermCareInvoiceLine(models.Model):
    invoice = models.ForeignKey(LongTermCareInvoiceFile, on_delete=models.CASCADE, related_name='invoice_line')
    start_period = models.DateField(_('Date Début période'), )
    end_period = models.DateField(_('Date Fin période'), blank=True, null=True)
    long_term_care_package = models.ForeignKey(LongTermPackage, on_delete=models.CASCADE,
                                               null=True, blank=True,
                                               related_name='long_term_care_package')
    paid = models.BooleanField(_('Paid'), default=False)
    refused_by_insurance = models.BooleanField(_('Refused by insurance'), default=False)
    comment = models.CharField(_('Comment'), max_length=500, blank=True, null=True)
    xml_invoice_reference = models.CharField(_('Référence de facturation'), max_length=255, blank=True, null=True)
    subcontractor = models.ForeignKey(
        SubContractor,
        on_delete=models.SET_NULL,
        related_name='long_term_invoice_lines',
        null=True,
        blank=True
    )
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def calculate_price(self):
        if self.paid or self.refused_by_insurance:
            return 0
        number_of_days_inclusive = (self.end_period - self.start_period).days + 1
        if self.long_term_care_package.package:
            return self.long_term_care_package.price_per_year_month(year=self.start_period.year,
                                                                    month=self.start_period.month) * number_of_days_inclusive
        else:
            raise ValidationError("Line seulement pour un forfait (package doit etre true)")

    def calculate_price_per_day(self):
        if not self.long_term_care_package.package:
            raise ValidationError("Line seulement pour un forfait (package doit etre false)")
        else:
            # price for specific care_date
            return self.long_term_care_package.price_per_year_month(year=self.start_period.year,
                                                                    month=self.start_period.month)

    def get_line_item_per_each_day_of_period(self):
        # loop through all days of period and create an object for each day
        number_of_days_inclusive = (self.end_period - self.start_period).days + 1
        data_to_return = []
        for day in range(number_of_days_inclusive):
            date_of_line = self.start_period + timedelta(days=day)
            # format date YYYYMMDD
            date_of_line_str = date_of_line.strftime("%Y%m%d")
            reference_prestation = "%s%s%s" % (self.invoice.id, self.long_term_care_package.id, date_of_line_str)
            data_to_return.append(
                LongTermCareInvoiceLinePerDay(reference_prestation, date_of_line, self.long_term_care_package))
        return data_to_return

    def get_line_item_per_each_day_of_period_not_paid(self):
        if self.paid:
            return []
        # loop through all days of period and create an object for each day
        number_of_days_inclusive = (self.end_period - self.start_period).days + 1
        data_to_return = []
        for day in range(number_of_days_inclusive):
            date_of_line = self.start_period + timedelta(days=day)
            # format date YYYYMMDD
            date_of_line_str = date_of_line.strftime("%Y%m%d")
            reference_prestation = "%s%s%s" % (self.invoice.id, self.long_term_care_package.id, date_of_line_str)
            data_to_return.append(
                LongTermCareInvoiceLinePerDay(reference_prestation, date_of_line, self.long_term_care_package))
        return data_to_return

    class Meta:
        verbose_name = _("Ligne de facture assurance dépendance")
        verbose_name_plural = _("Lignes de facture assurance dépendance")

    def validate_lines_are_same_period(self):
        long_term_invoice = self.invoice
        if self.start_period.month != long_term_invoice.invoice_start_period.month or self.start_period.year != long_term_invoice.invoice_start_period.year:
            raise ValidationError("La ligne doit être dans le même mois que la facture sur la ligne %s" % self)
        if self.end_period.month != long_term_invoice.invoice_end_period.month or self.end_period.year != long_term_invoice.invoice_end_period.year:
            raise ValidationError("La ligne doit être dans le même mois que la facture sur la ligne %s" % self)

    def validate_lines_are_made_by_correct_sub_contractor(self):
        if self.subcontractor:
            if not PatientSubContractorRelationship.objects.filter(patient=self.invoice.patient,
                                                                   subcontractor=self.subcontractor).exists():
                # list of all sub contractors for this patient
                sub_contractors = PatientSubContractorRelationship.objects.filter(patient=self.invoice.patient)
                raise ValidationError(
                    "Le sous-traitant de la ligne doit être le même que celui du patient (%s)" % sub_contractors)

    def validate_line_are_coherent_with_medical_care_summary_per_patient(self):
        plan_for_period = get_summaries_between_two_dates(self.invoice.patient, self.start_period, self.end_period)
        if not plan_for_period or len(plan_for_period) == 0:
            raise ValidationError("Aucune synthèse trouvée pour cette période")
        if len(plan_for_period) > 1:
            raise ValidationError("Trop de synthèses %s" % len(plan_for_period))
        famdm_count = MedicalCareSummaryPerPatientDetail.objects.filter(
            medical_care_summary_per_patient=plan_for_period[0].medicalSummaryPerPatient.id,
            item__code="AMD-M").count()
        if "FAMDM" == self.long_term_care_package.code and famdm_count == 0:
            raise ValidationError("Le forfait FAMDM n'a pas été encodé dans la synthèse")
        elif "FAMDM" != self.long_term_care_package.code:
            if plan_for_period[0].packageLevel and plan_for_period[
                0].packageLevel != self.long_term_care_package.dependence_level:
                raise ValidationError(
                    "Le forfait dépendance {0} - {1} encodé ne correspond pas à la synthèse {2}".format(
                        self.long_term_care_package,
                        self.long_term_care_package.dependence_level,
                        plan_for_period[0].medicalSummaryPerPatient.nature_package))
            if plan_for_period[0].medicalSummaryPerPatient.nature_package is None and plan_for_period[
                0].medicalSummaryPerPatient.level_of_needs != self.long_term_care_package.dependence_level:
                raise ValidationError(
                    "Le forfait dépendance {0} - {1} encodé ne correspond pas à la synthèse {2}".format(
                        self.long_term_care_package,
                        self.long_term_care_package.dependence_level,
                        plan_for_period[0].medicalSummaryPerPatient.level_of_needs))

    def __str__(self):
        return "Ligne de facture assurance dépendance de {0} à {1} patient {2}".format(self.start_period,
                                                                                       self.end_period,
                                                                                       self.invoice.patient)
