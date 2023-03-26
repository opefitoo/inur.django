from xml.etree.ElementTree import ElementTree

import xmlschema
from constance import config
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from invoices.enums.event import EventTypeEnum
from invoices.events import Event
from invoices.models import Patient


class LongTermCareInvoiceFile(models.Model):

    # invoice year is positive integer
    year = models.PositiveIntegerField(_('Year'))
    # invoice month
    month = models.PositiveIntegerField(_('Month'))
    invoice_sent_date = models.DateField(_('Invoice Sent Date'),  default=timezone.now)
    generated_invoice_file = models.FileField(_('Generated Invoice File'), )
    force_regeneration = models.BooleanField(_('Force Regeneration'), default=False)
    generation_report = models.TextField(_('Generation Report'),)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient')
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)


    class Meta:
        unique_together = ('year', 'month')
        verbose_name = _("Facture assurance dépendance")
        verbose_name_plural = _("Factures assurance dépendance")

    def __str__(self):
        return "Facture assurance dépendance de {0}/{1}".format(self.month, self.year)

    # on save gather all events for the month and generate the invoice file
    def save(self, *args, **kwargs):
        # gather all events for the month
        all_events = Event.objects.filter(date__year=self.year, date__month=self.month,
                                          event_type_enum=EventTypeEnum.ASS_DEP,
                                          state=Event.STATES.DONE)

        # generate invoice file
        # save invoice file
        # save invoice file
        super(LongTermCareInvoiceFile, self).save(*args, **kwargs)

    def generate_xml(self):
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
        dateEnvoi.text = self.invoice_sent_date.strftime("%Y-%m-%d")
        referenceFichierFacturation = ElementTree.SubElement(entete, "referenceFichierFacturation")
        referenceFichierFacturation.text = "19" + self.invoice_sent_date.strftime("%Y%m%d")
        periodeDecompte = ElementTree.SubElement(entete, "periodeDecompte")
        exercice = ElementTree.SubElement(periodeDecompte, "exercice")
        exercice.text = str(self.year)
        mois = ElementTree.SubElement(periodeDecompte, "mois")
        mois.text = str(self.month)
        demandeDecompte = ElementTree.SubElement(entete, "demandeDecompte")
        nombre = ElementTree.SubElement(demandeDecompte, "nombre")
        devise = ElementTree.SubElement(demandeDecompte, "devise")
        devise.text = "EUR"
        montantBrut = ElementTree.SubElement(demandeDecompte, "montantBrut")
        montantBrut.text = "0"
        montantNet = ElementTree.SubElement(demandeDecompte, "montantNet")
        montantNet.text = "0"
        passages = ["2023-02-28"]
        i = 0
        for passage in passages:
            facture = ElementTree.SubElement(root, "facture")
            referenceFacture = ElementTree.SubElement(facture, "referenceFacture")
            referenceFacture.text = "19" + passage.strftime("%Y%m%d")
            numeroOrdreFacture = ElementTree.SubElement(facture, "numeroOrdreFacture")
            numeroOrdreFacture.text = str(i)
            identifiantPersonneProtegee = ElementTree.SubElement(facture, "identifiantPersonneProtegee")
            identifiantPersonneProtegee.text = passage.person_id
            dateEtablissementFacture = ElementTree.SubElement(facture, "dateEtablissementFacture")
            dateEtablissementFacture.text = passage.strftime("%Y-%m-%d")
            acte = ElementTree.SubElement(facture, "acte")
            codeTarif = ElementTree.SubElement(acte, "codeTarif")
            codeTarif.text = "505"
            #periodePrestation = ElementTree.SubElement(prestation, "periodePrestation")
        pass
