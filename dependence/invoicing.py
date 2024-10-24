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
    description = models.TextField(_('Description'), blank=True, null=True)
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

    def get_invoices(self):
        return LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all().order_by('id')

    def display_longTermCareInvoiceFiles(self):
        return mark_safe('<br>'.join([f"{invoice}" for invoice in self.get_invoices]))

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
        montantBrut.text = str(self.calculate_total_price_to_be_sent_to_CNS())
        # create sub element montantNet
        montantNet = ElementTree.SubElement(demandeDecompte, "montantNet")
        montantNet.text = str(self.calculate_total_price_to_be_sent_to_CNS())
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
                montantBrut.text = str(item.calculate_price_to_be_sent_to_CNS())
                # create sub element montantNet
                montantNet = ElementTree.SubElement(demandePrestation, "montantNet")
                montantNet.text = str(item.calculate_price_to_be_sent_to_CNS())
                # create sub element identifiantExecutant
                identifiantExecutant = ElementTree.SubElement(prestation, "identifiantExecutant")
                if item.subcontractor and item.long_term_care_package.code in ("AMDGG", "AAIG"):
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
            montantBrut.text = str(invoice.calculate_price_to_be_sent_to_CNS())
            # create sub element montantNet
            montantNet = ElementTree.SubElement(demandeFacture, "montantNet")
            montantNet.text = str(invoice.calculate_price_to_be_sent_to_CNS())
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

    def calculate_total_price_to_be_sent_to_CNS(self):
        total_price = 0
        for invoice in LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all():
            total_price += invoice.calculate_price_to_be_sent_to_CNS()
        return total_price

    def total_price_formatted(self):
        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')  # Unix/Linux/MacOS
        # locale.setlocale(locale.LC_ALL, 'french')  # Windows
        return locale.format_string("%.2f", self.calculate_total_price_to_be_sent_to_CNS(), grouping=True, monetary=True)

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
    link_to_monthly_statement = models.ForeignKey(LongTermCareMonthlyStatement, on_delete=models.PROTECT,
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
    # if element has key 'anomaliePrestation' and its value is not None, return False
    return 'anomaliePrestation' not in element or element['anomaliePrestation'] is None

def detect_anomalies(instance):
    # Get the current script's directory
    current_directory = os.path.dirname(os.path.abspath(__file__))
    # Parse the XML file
    # Load the XSD schema file
    xsd_path = os.path.join(current_directory, 'xsd', 'ad-fichierfacturationretour-506.xsd')
    xsd_schema = xmlschema.XMLSchema(xsd_path)

    #xml_file = instance.received_invoice_file_response.storage.open(instance.received_invoice_file_response.name)

    # Parse and validate the XML document
    try:
        xml_document = xsd_schema.to_dict(instance.received_invoice_file_response.file)
    except xmlschema.XMLSchemaValidationError as e:
        print(f"XML document is not valid: {e}")
        return

    # Now xml_document is a Python dictionary that represents your XML document
    # You can navigate and validate the XML document using standard Python dictionary operations

    # Extract montantBrut and montantNet
    montant_brut = xml_document['fichierFacturation']['montantBrut']
    montant_net = xml_document['fichierFacturation']['montantNet']

    # Compare montantBrut and montantNet
    if montant_brut != montant_net:
        print(f"Warning: montantBrut ({montant_brut}) and montantNet ({montant_net}) are not equal.")

        # parse the xml sent to find the invoice
        # Parse the XML file
        invoice_tree = ET.parse(instance.xml_invoice_file)
        invoice_root = invoice_tree.getroot()

        # Extract facture elements with anomalies
        anomalies = []
        # loop through all 'facture' elements in xml_document
        for facture in xml_document['fichierFacturation']['facture']:
        #for facture in invoice_root.findall('.//facture'):
            anomaliesFactures = None
            reference_facture = facture['referenceFacture'] if facture['referenceFacture'] is not None else "Unknown"
            # check if there's  'anomalieFacture' key first in facture element
            if 'anomalieFacture' in facture and facture['anomalieFacture'] is not None:
                anomaliesFactures = facture['anomalieFacture']
            items = LongTermCareInvoiceFile.objects.annotate(
                invoice_reference_filter=Concat(
                    ExtractYear('invoice_start_period'),
                    ExtractMonth('invoice_start_period'),
                    F('id'),
                    output_field=CharField()
                )
            )
            if anomaliesFactures is not None:
                # find prestation without anomalies
                # Manually filter the prestations
                prestations_without_anomalies = [prestation for prestation in facture['prestation'] if
                                                 has_no_anomalie_prestation(prestation)]
                invoice_in_error = items.filter(invoice_reference_filter=reference_facture).get()
                for prestation in prestations_without_anomalies:
                    invoiced_prestation = invoice_root.find('.//facture/prestation/[referencePrestation="{}"]'.format(
                        prestation['referencePrestation']))
                    date_prestation_text = invoiced_prestation.find('periodePrestation/dateDebut').text
                    date_prestation = date.fromisoformat(date_prestation_text)
                    invoiced_code_acte = invoiced_prestation.find('acte/codeTarif').text
                    reference_prestation = prestation['referencePrestation']
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
                error_messages = []
                for anom in anomaliesFactures:
                    error_messages.append(f"Facture {reference_facture} has anomaly {anom['code']} - {anom['motif']}")
                # Find all 'prestation' elements with 'anomaliePrestation' child within the current 'facture'
                prestations_with_anomalies = [prestation for prestation in facture['prestation'] if not has_no_anomalie_prestation(prestation)]
                for prestation in prestations_with_anomalies:
                    # find the invoiced prestation from the invoice file
                    invoiced_prestation = invoice_root.find('.//facture/prestation/[referencePrestation="{}"]'.format(
                        prestation['referencePrestation']))
                    date_prestation_text = invoiced_prestation.find('periodePrestation/dateDebut').text
                    date_prestation = date.fromisoformat(date_prestation_text)
                    invoiced_code_acte = invoiced_prestation.find('acte/codeTarif').text
                    reference_prestation = prestation['referencePrestation']
                    anomaliesPrestations = prestation['anomaliePrestation']
                    anomlies_text = ""
                    for anomalie in anomaliesPrestations:
                        anomalie_type = anomalie['type']
                        anomalie_code = anomalie['code']
                        anomalie_motif = anomalie['motif']
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
                    code_acte_paye = prestation['codeActePaye']
                    anomalies = prestation['anomaliePrestation']
                    anomaliesPrestationsText = ""
                    for anomalie in anomalies:
                        anomalie_type = anomalie['type']
                        anomalie_code = anomalie['code']
                        anomalie_motif = anomalie['motif']
                        anomaliesPrestationsText += f"Type: {anomalie_type} - Code: {anomalie_code} - Motif: {anomalie_motif}"
                    # prestation reference looks like "%s%s%s" % (self.invoice.id, self.long_term_care_package.id, date_of_line_str) extract long_term_care_package.id knowing that invoice.id is invoice_in_error.id
                    long_term_care_package_id = reference_prestation[len(str(invoice_in_error.id)):-10]
                    print(long_term_care_package_id)
                    long_term_care_package = LongTermPackage.objects.get(code=code_acte_paye)

                    # Display the extracted information
                    print(f"  - Prestation Reference: {reference_prestation} - anomalies : {anomaliesPrestationsText}")
                    error_messages.append(
                        f"reference prestation : {reference_prestation} - Error messages: {anomaliesPrestationsText}")

                # generate a hash for all error_messages
                error_messages_hash = hashlib.sha256(str(error_messages).encode('utf-8')).hexdigest()
                # check if error message already exists
                if not InvoiceError.objects.filter(invoice=invoice_in_error,
                                                   statement_sending=instance).exists():
                    InvoiceError.objects.create(invoice=invoice_in_error,
                                                statement_sending=instance,
                                                error_message=error_messages)
                    print(f"Facture {invoice_in_error} has anomaly {error_messages}")
                else:
                    print(f"deleting error message for facture {invoice_in_error} and sending {instance}")
                    InvoiceError.objects.filter(invoice=invoice_in_error,
                                                statement_sending=instance).delete()
                # appends anomaliesFactures to anomalies
                anomalies.append((reference_facture, anomaliesFactures))
                #anomalies.append((reference_facture, code, motif))
            else:
                print(f"Facture {reference_facture} has no anomalies")
                montant_net_facture = facture['montantNet']
                montant_brut_facture = facture['montantBrut']
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
    link_to_monthly_statement = models.ForeignKey(LongTermCareMonthlyStatement, on_delete=models.PROTECT,
                                                  related_name='monthly_statement', blank=True, null=True)
    # invoice year is positive integer
    invoice_start_period = models.DateField(_('Invoice Start Period'), )
    invoice_end_period = models.DateField(_('Invoice End Period'), )
    # patient only under dependance_insurance
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient',
                                limit_choices_to=Q(is_under_dependence_insurance=True))
    long_term_invoice_file_that_corrects = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True)
    invoice_sequence_number = models.PositiveIntegerField(_('Invoice Sequence Number'), default=1)
    invoice_to_be_sent_to_CNS = models.BooleanField(_('Invoice to be sent to CNS'), default=True)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def add_line_forfait(self, forfait_number, date_of_care, subcontractor):
        # add a line forfait to the invoice
        # get the forfait
        forfait = LongTermPackage.objects.get(code="AEVF%s" % forfait_number)
        # create a line forfait
        LongTermCareInvoiceLine.objects.get_or_create(invoice=self, long_term_care_package=forfait,
                                                      start_period=date_of_care,
                                               end_period=date_of_care, comment="Added from script Forfait %s" % forfait_number,
                                                        subcontractor=subcontractor)
        return
    def add_item_with_code(self, code, date_of_care, quantity, subcontractor):
        # add a line forfait to the invoice
        # get the forfait
        aevcare = LongTermPackage.objects.get(code=code)
        # create a line forfait
        LongTermCareInvoiceItem.objects.get_or_create(invoice=self,
                                                      long_term_care_package=aevcare,
                                                      care_date=date_of_care,
                                                      quantity=quantity,
                                                      comment="Added from script %s" % code,
                                                        subcontractor=subcontractor)
        return

    @property
    def has_subcontractor(self):
        # if there's no subcontractor, return False, if not return a conactenad list of subcontractors
        subcontractors = []
        for line in LongTermCareInvoiceLine.objects.filter(invoice=self).all():
            if line.subcontractor:
                # take the 4 first characters of the contractor name
                subcontractors.append(line.subcontractor.get_abbreviated_name())
        for item in LongTermCareInvoiceItem.objects.filter(invoice=self).all():
            if item.subcontractor:
                subcontractors.append(item.subcontractor.get_abbreviated_name())
        if len(subcontractors) == 0:
            return False
        # return a nice string
        return ", ".join(set(subcontractors))
    def link_operation_invoice_to_monthly_statement(self, LongTermCareMonthlyStatement_id=None):
        # link the invoice to the monthly statement
        # get the monthly statement
        if LongTermCareMonthlyStatement_id:
            monthly_statement = LongTermCareMonthlyStatement.objects.get(id=LongTermCareMonthlyStatement_id)
        else:
            monthly_statement = LongTermCareMonthlyStatement.objects.create(year=self.invoice_start_period.year,
                                                                        month=self.invoice_start_period.month)
        if monthly_statement:
            self.link_to_monthly_statement = monthly_statement
            self.save()
        else:
            raise ValidationError("Le décompte mensuel n'existe pas")
        return monthly_statement.id

    # must be linked to a monthly statement that is same period as invoice file
    def clean(self):
        if self.invoice_to_be_sent_to_CNS:
            # MedicalCareSummaryPerPatient
            if self.link_to_monthly_statement and self.link_to_monthly_statement.month != self.invoice_start_period.month:
                raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
            if self.link_to_monthly_statement and self.link_to_monthly_statement.year != self.invoice_start_period.year:
                raise ValidationError("L'année de la facture doit être la même que l'année du décompte mensuel")
            if self.link_to_monthly_statement and self.link_to_monthly_statement.month != self.invoice_end_period.month:
                raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
            if self.link_to_monthly_statement and self.link_to_monthly_statement.year != self.invoice_end_period.year:
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

    def copy_prestations_in_error_to_new_invoice(self):
        # copy all prestations in error to a new invoice
        # create a new invoice
        new_invoice = LongTermCareInvoiceFile.objects.create(invoice_start_period=self.invoice_start_period,
                                                             invoice_end_period=self.invoice_end_period,
                                                             patient=self.patient)
        # get all prestations in error
        prestations_in_error = LongTermCareInvoiceLine.objects.filter(invoice=self).filter(refused_by_insurance=True).all()
        for prestation in prestations_in_error:
            prestation.pk = None
            prestation.invoice = new_invoice
            prestation.refused_by_insurance = False
            prestation.save()
        prestations_in_error = LongTermCareInvoiceItem.objects.filter(invoice=self).filter(refused_by_insurance=True).all()
        for prestation in prestations_in_error:
            prestation.pk = None
            prestation.invoice = new_invoice
            prestation.refused_by_insurance = False
            prestation.save()

        #for prestation in prestations_in_error:
        #    prestation.invoice = new_invoice
        #    prestation.save()
        return new_invoice

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

    def calculate_price_to_be_sent_to_CNS(self):
        lines = LongTermCareInvoiceLine.objects.filter(invoice=self)
        total = 0
        for line in lines:
            total += line.calculate_price()
        items = LongTermCareInvoiceItem.objects.filter(invoice=self)
        for item in items:
            total += item.calculate_price_to_be_sent_to_CNS()
        total_price = round(total, 2)
        return total_price

    def total_number_of_lines(self):
        _number_of_lines = 0
        for line in LongTermCareInvoiceLine.objects.filter(
                invoice=self).all():
            if line.paid or line.refused_by_insurance:
                continue
            _number_of_lines += len(line.get_line_item_per_each_day_of_period_not_paid())
        return _number_of_lines + LongTermCareInvoiceItem.objects.filter(
            invoice=self, paid=False, refused_by_insurance=False).count()

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

    def get_formatted_care_date(self):
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
        # should be Lundi 01/01/2021 explictly transalted to FRENCH
        return self.care_date.strftime("%A %d/%m/%Y")

    class Meta:
        verbose_name = _("Item facture assurance dépendance")
        verbose_name_plural = _("Item de facture assurance dépendance")

    # get who really did the care
    def get_caregiver(self):
        if self.subcontractor:
            relationship = PatientSubContractorRelationship.objects.filter(patient=self.invoice.patient, subcontractor=self.subcontractor).get()
            if relationship.relationship_type == PatientSubContractorRelationship.RELATIONSHIP_TYPE_CHOICES[0][0]:
                return InvoicingDetails.objects.filter(default_invoicing=True).first().name
            else:
                return self.subcontractor
    def calculate_price(self, take_paid_or_refused_by_insurance_into_account=True, take_subcontractor_into_account=True):
        if take_paid_or_refused_by_insurance_into_account and (self.paid or self.refused_by_insurance):
            return 0
        else:
            if self.subcontractor and take_subcontractor_into_account:
                # - billing_retrocession % of price
                return round(self.long_term_care_package.price_per_year_month(year=self.care_date.year,
                                                                        month=self.care_date.month) * Decimal(str(self.quantity)) * (
                                1 - self.subcontractor.billing_retrocession / 100), 2)

            if self.long_term_care_package.package:
                raise ValidationError("Item seulement pour un non forfait (package doit etre false)")
            else:
                # price for specific care_date
                return round(self.long_term_care_package.price_per_year_month(year=self.care_date.year,
                                                                        month=self.care_date.month) * Decimal(str(self.quantity)), 2)

    def calculate_price_to_be_sent_to_CNS(self, take_paid_or_refused_by_insurance_into_account=True):
        return self.calculate_price(take_paid_or_refused_by_insurance_into_account=take_paid_or_refused_by_insurance_into_account,
                                    take_subcontractor_into_account=False)
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
    def gross_unit_price(self):
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
    skip_aev_check = models.BooleanField(_('Skip AEV Check'), default=False)
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

    def get_line_care_givers(self):
        if self.subcontractor:
            relationship = PatientSubContractorRelationship.objects.filter(patient=self.invoice.patient, subcontractor=self.subcontractor).get()
            if relationship.relationship_type == PatientSubContractorRelationship.RELATIONSHIP_TYPE_CHOICES[0][0]:
                return InvoicingDetails.objects.filter(default_invoicing=True).first().name
            else:
                return self.subcontractor
    def calculate_quantity_on_line_period(self):
        number_of_days_inclusive = (self.end_period - self.start_period).days + 1
        return number_of_days_inclusive

    def calculate_price(self):
        if self.paid or self.refused_by_insurance:
            return 0
        number_of_days_inclusive = (self.end_period - self.start_period).days + 1
        if self.long_term_care_package.package:
            # deduct the retrocession in case of subcontractor
            if self.subcontractor:
                return self.long_term_care_package.price_per_year_month(year=self.start_period.year,
                                                                    month=self.start_period.month) * number_of_days_inclusive * ( 1 - self.subcontractor.billing_retrocession / 100)
            return self.long_term_care_package.price_per_year_month(year=self.start_period.year, month=self.start_period.month) * number_of_days_inclusive

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
