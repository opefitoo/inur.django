import calendar
import locale
import os
from dataclasses import dataclass
from datetime import timedelta, date
from xml.etree import ElementTree

import xmlschema
from constance import config
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dependence.detailedcareplan import MedicalCareSummaryPerPatient, get_summaries_between_two_dates
from dependence.longtermcareitem import LongTermCareItem, LongTermPackage
from invoices.employee import Employee
from invoices.models import Patient
from invoices.modelspackage import InvoicingDetails


# décompte mensuel de factures
class LongTermCareMonthlyStatement(models.Model):
    class Meta:
        verbose_name = _("Décompte mensuel de factures")
        verbose_name_plural = _("Décomptes mensuels de factures")

    year = models.PositiveIntegerField(_('Year'))
    # invoice month
    month = models.PositiveIntegerField(_('Month'))
    generated_invoice_file = models.FileField(_('Generated Invoice File'), blank=True, null=True)
    force_regeneration = models.BooleanField(_('Force Regeneration'), default=False)
    # dateEnvoi
    date_of_submission = models.DateField(_('Date d\'envoi du fichier'), blank=True, null=True)
    # dateReception
    generated_invoice_file_response = models.FileField(_('Generated Invoice Response File'), blank=True, null=True)
    date_of_receipt = models.DateField(_('Date de réception du fichier'), blank=True, null=True)

    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def generate_xml_using_xmlschema(self):

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
        dateEnvoi = ElementTree.SubElement(entete, "dateEnvoi")
        dateEnvoi.text = self.date_of_submission.strftime("%Y-%m-%d")
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
        nombre.text = "10"
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
        for invoice in LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all():
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
            dateEtablissementFacture = ElementTree.SubElement(facture, "dateEtablissementFacture")
            dateEtablissementFacture.text = self.date_of_submission.strftime("%Y-%m-%d")
            # loop through all LongTermCareInvoiceLine
            _counter = 0
            for item in LongTermCareInvoiceItem.objects.filter(invoice=invoice).all().all():
                _counter += 1
                # create sub element prestation
                prestation = ElementTree.SubElement(facture, "prestation")
                # create sub element codePrestation
                referencePrestation = ElementTree.SubElement(prestation, "referencePrestation")
                referencePrestation.text = str(_counter)
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
                nombre.text = str(2)
                # create sub element devise
                devise = ElementTree.SubElement(demandePrestation, "devise")
                devise.text = "EUR"
                # create sub element montantBrut
                montantBrut = ElementTree.SubElement(demandePrestation, "montantBrut")
                montantBrut.text = str(item.long_term_care_package.price_per_year_month(year=self.year,
                                                                                            month=self.month))
                # create sub element montantNet
                montantNet = ElementTree.SubElement(demandePrestation, "montantNet")
                montantNet.text = str(item.long_term_care_package.price_per_year_month(year=self.year,
                                                                                        month=self.month))
                # create sub element identifiantExecutant
                identifiantExecutant = ElementTree.SubElement(prestation, "identifiantExecutant")
                identifiantExecutant.text = config.CODE_PRESTATAIRE

            for line in LongTermCareInvoiceLine.objects.filter(invoice=invoice).all().all():
                for line_per_day in line.get_line_item_per_each_day_of_period():
                    _counter += 1
                    # create sub element prestation
                    prestation = ElementTree.SubElement(facture, "prestation")
                    # create sub element codePrestation
                    referencePrestation = ElementTree.SubElement(prestation, "referencePrestation")
                    referencePrestation.text = str(_counter)
                    # create sub element acte
                    acte = ElementTree.SubElement(prestation, "acte")
                    # create sub element codeTarif
                    codeTarif = ElementTree.SubElement(acte, "codeTarif")
                    codeTarif.text = line.long_term_care_package.code
                    # create sub element periodePrestation
                    periodePrestation = ElementTree.SubElement(prestation, "periodePrestation")
                    # create sub element dateDebut
                    dateDebut = ElementTree.SubElement(periodePrestation, "dateDebut")
                    #dateDebut.text = line.start_period.strftime("%Y-%m-%d")
                    dateDebut.text = line_per_day.care_date.strftime("%Y-%m-%d")
                    # create sub element dateFin
                    #dateFin = ElementTree.SubElement(periodePrestation, "dateFin")
                    #dateFin.text = line.end_period.strftime("%Y-%m-%d")

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
                    montantBrut.text = str(line.long_term_care_package.price_per_year_month(year=self.year,
                                                                                            month=self.month))
                    # create sub element montantNet
                    montantNet = ElementTree.SubElement(demandePrestation, "montantNet")
                    montantNet.text = str(line.long_term_care_package.price_per_year_month(year=self.year,
                                                                                            month=self.month))
                    # create sub element identifiantExecutant
                    identifiantExecutant = ElementTree.SubElement(prestation, "identifiantExecutant")
                    identifiantExecutant.text = config.CODE_PRESTATAIRE
            # create sub element demandeFacture
            demandeFacture = ElementTree.SubElement(facture, "demandeFacture")
            # create sub element nombre
            nombre = ElementTree.SubElement(demandeFacture, "nombre")
            nombre.text = "1"
            # create sub element devise
            devise = ElementTree.SubElement(demandeFacture, "devise")
            devise.text = "EUR"
            # create sub element montantBrut
            montantBrut = ElementTree.SubElement(demandeFacture, "montantBrut")
            montantBrut.text = str(self.calculate_total_price())
            # create sub element montantNet
            montantNet = ElementTree.SubElement(demandeFacture, "montantNet")
            montantNet.text = str(self.calculate_total_price())
        # create a new XML file with the results
        mydata = ElementTree.tostring(root)
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
    @property
    def get_invoices(self):
        return LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().all()

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
        return LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement=self).all().count()

    @property
    def get_month_in_2_digits(self):
        return str(self.month).zfill(2)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.force_regeneration:
            # create invoice file
            xml_str = self.generate_xml_using_xmlschema()
            print(xml_str)

    def __str__(self):
            return f"{self.year} - {self.month}"


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
        self.validate_lines_are_same_period()
        # MedicalCareSummaryPerPatient
        if self.link_to_monthly_statement.month != self.invoice_start_period.month:
            raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
        if self.link_to_monthly_statement.year != self.invoice_start_period.year:
            raise ValidationError("L'année de la facture doit être la même que l'année du décompte mensuel")
        if self.link_to_monthly_statement.month != self.invoice_end_period.month:
            raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
        if self.link_to_monthly_statement.year != self.invoice_end_period.year:
            raise ValidationError("L'année de la facture doit être la même que l'année du décompte mensuel")

    def validate_lines_are_same_period(self):
        lines = LongTermCareInvoiceLine.objects.filter(invoice=self)
        for line in lines:
            if line.start_period.month != self.invoice_start_period.month or line.start_period.year != self.invoice_start_period.year:
                raise ValidationError("La ligne doit être dans le même mois que la facture")
            if line.end_period.month != self.invoice_end_period.month or line.end_period.year != self.invoice_end_period.year:
                raise ValidationError("La ligne doit être dans le même mois que la facture")

    def calculate_price(self):
        lines = LongTermCareInvoiceLine.objects.filter(invoice=self)
        total = 0
        for line in lines:
            total += line.calculate_price()
        items = LongTermCareInvoiceItem.objects.filter(invoice=self)
        for item in items:
            total += item.calculate_price()
        return total

    @property
    def get_invoice_items(self):
        # get LongTermCareInvoiceItem linked to this invoice
        if self.id:
            return LongTermCareInvoiceItem.objects.filter(invoice=self).order_by(
                'care_date')
        return None

    @property
    def get_invoice_lines(self):
        # get LongTermCareInvoiceItem linked to this invoice
        if self.id:
            return LongTermCareInvoiceLine.objects.filter(invoice=self).order_by(
                'start_period')
        return None

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

    def __str__(self):
        return "Ligne de facture assurance dépendance de {0} patient {1}".format(self.item_date,
                                                                                 self.invoice.patient)


class LongTermCareInvoiceItem(models.Model):
    invoice = models.ForeignKey(LongTermCareInvoiceFile, on_delete=models.CASCADE, related_name='invoice_item')
    care_date = models.DateField(_('Date Début période'), )
    long_term_care_package = models.ForeignKey(LongTermPackage, on_delete=models.CASCADE,
                                               related_name='from_item_to_long_term_care_package')
    quantity = models.IntegerField(_('Quantité'), default=1)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        return "Item de facture assurance dépendance de {0} patient {1}".format(self.care_date,
                                                                                 self.invoice.patient)

    class Meta:
        verbose_name = _("Item facture assurance dépendance")
        verbose_name_plural = _("Item de facture assurance dépendance")

    def calculate_price(self):
        if self.long_term_care_package.package:
            raise ValidationError("Item seulement pour un non forfait (package doit etre false)")
        else:
            # price for specific care_date
            return self.long_term_care_package.price_per_year_month(year=self.care_date.year,
                                                                    month=self.care_date.month) * self.quantity


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
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def calculate_price(self):
        number_of_days_inclusive = (self.end_period - self.start_period).days + 1
        if self.long_term_care_package.package:
            return self.long_term_care_package.price_per_year_month(year=self.start_period.year,
                                                                    month=self.start_period.month) * number_of_days_inclusive
        else:
            raise ValidationError("Line seulement pour un forfait (package doit etre true)")

    def get_line_item_per_each_day_of_period(self):
        # loop through all days of period and create an object for each day
        number_of_days_inclusive = (self.end_period - self.start_period).days + 1
        data_to_return = []
        for day in range(number_of_days_inclusive):
            date_of_line = self.start_period + timedelta(days=day)
            # format date YYYYMMDD
            date_of_line_str = date_of_line.strftime("%Y%m%d")
            reference_prestation = "%s%s%s" % (self.invoice.id, self.long_term_care_package.id, date_of_line_str )
            data_to_return.append(LongTermCareInvoiceLinePerDay(reference_prestation, date_of_line, self.long_term_care_package))
        return data_to_return

    class Meta:
        verbose_name = _("Ligne de facture assurance dépendance")
        verbose_name_plural = _("Lignes de facture assurance dépendance")

    def clean(self):
        self.validate_line_are_coherent_with_medical_care_summary_per_patient()

    def validate_line_are_coherent_with_medical_care_summary_per_patient(self):
        medical_care_summary_per_patient = MedicalCareSummaryPerPatient.objects.filter(patient=self.invoice.patient,
                                                                                       date_of_decision__lte=self.start_period)
        if medical_care_summary_per_patient.count() == 0:
            raise ValidationError("Aucune synthèse trouvée pour ce patient")
        plan_for_period = get_summaries_between_two_dates(self.invoice.patient, self.start_period, self.end_period)
        if not plan_for_period:
            raise ValidationError("Aucune synthèse trouvée pour cette période")
        if len(plan_for_period) > 1:
            raise ValidationError("Trop de synthèses %s" % len(plan_for_period))
        if plan_for_period[0].medicalSummaryPerPatient.nature_package != self.long_term_care_package.dependence_level:
            raise ValidationError("Le forfait dépendance {0} - {1} encodé ne correspond pas à la synthèse {2}".format(
                self.long_term_care_package,
                self.long_term_care_package.dependence_level,
                plan_for_period[0].medicalSummaryPerPatient.nature_package))

    def __str__(self):
        return "Ligne de facture assurance dépendance de {0} à {1} patient {2}".format(self.start_period,
                                                                                       self.end_period,
                                                                                       self.invoice.patient)

# @receiver(post_save, sender=LongTermCareInvoiceFile, dispatch_uid="generate_invoice_file_and_notify_via_chat_5QH9cN")
# def parse_xml_and_notify_via_chat(sender, instance, **kwargs):
#     if instance.generated_invoice_file:
#         message = "Le fichier de facture %s a été mis à jour." % instance.generated_invoice_file
#     if instance.force_regeneration:
#         generate_invoice_file(instance)
#         notify_system_via_google_webhook(message)
#         return
