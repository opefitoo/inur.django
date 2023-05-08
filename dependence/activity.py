import os

import lxml.etree as ElementTree
import xmlschema
from constance import config
from django.db import models
from django.utils.translation import gettext_lazy as _

from dependence.longtermcareitem import LongTermCareItem


class LongTermMonthlyActivityFile(models.Model):
    class Meta:
        verbose_name = _("Fichier d'activité mensuel")
        verbose_name_plural = _("Fichiers d'activité mensuels")

    year = models.PositiveIntegerField(_('Year'))
    # invoice month
    month = models.PositiveIntegerField(_('Month'))
    provider_date_of_sending = models.DateField(_('Provider Date of Sending'))
    file = models.FileField(upload_to='longtermmonthlyactivityfiles/')
    version_number = models.PositiveIntegerField(_('Version Number'))
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    # link to the LongTermMonthlyActivity model
    monthly_activities = models.ManyToManyField('LongTermMonthlyActivity', verbose_name=_("Activities"),
                                                blank=True)

    def generate_xml_using_xmlschema(self):
        # Load the XSD schema file
        # go one folder up
        # Get the current script's directory
        current_directory = os.path.dirname(os.path.abspath(__file__))

        # Construct the path to the XSD file
        xsd_path = os.path.join(current_directory, 'xsd', 'ad-declaration-14.xsd')

        # Load the XSD schema
        xsd_schema = xmlschema.XMLSchema(xsd_path)

        # xsd_schema = xmlschema.XMLSchema(settings.BASE_DIR + '/dependence/xsd/ad-declaration-14.xsd')
        # create element tree object
        root = ElementTree.Element("Declarations")
        # create sub element Type
        Type = ElementTree.SubElement(root, "Type")
        # create sub element CadreLegal
        CadreLegal = ElementTree.SubElement(Type, "CadreLegal")
        CadreLegal.text = "ASD"
        # create sub element Layout
        Layout = ElementTree.SubElement(Type, "Layout")
        Layout.text = "1"
        # create sub element Type
        Type = ElementTree.SubElement(Type, "Type")
        Type.text = "DCL"
        # create sub element Organisme
        Organisme = ElementTree.SubElement(root, "Organisme")
        Organisme.text = "19"
        # create sub element DateEnvoiPrestataire
        DateEnvoiPrestataire = ElementTree.SubElement(root, "DateEnvoiPrestataire")
        DateEnvoiPrestataire.text = self.provider_date_of_sending.strftime("%Y-%m-%d")
        # create sub element Prestataire
        Prestataire = ElementTree.SubElement(root, "Prestataire")
        Prestataire.text = config.CODE_PRESTATAIRE
        # loop through all LongTermMonthlyActivityDetail objects
        # create sub element Changement
        activities = LongTermMonthlyActivity.objects.filter(year=self.year, month=self.month).all()
        # Activites
        for activity in activities:
            Activites = ElementTree.SubElement(root, "Activites")
            # create child element Activity
            DclTypeActivite = ElementTree.SubElement(Activites, "TypeActivite")
            DclTypeActivite.text = "DECLARATION"
            PersonneProtegee = ElementTree.SubElement(Activites, "PersonneProtegee")
            PersonneProtegee.text = activity.patient.code_sn
            ReferenceActivite = ElementTree.SubElement(Activites, "ReferenceActivite")
            ReferenceActivite.text = str(activity.id)
            dtls = LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=activity).all()
            for dtl in dtls:
                Activite = ElementTree.SubElement(Activites, "Activite")
                AevTypeActivite = ElementTree.SubElement(Activite, "TypeActivite")
                AevTypeActivite.text = "AEV"
                # DateActivite
                DateActivite = ElementTree.SubElement(Activite, "DateActivite")
                DateActivite.text = dtl.activity_date.strftime("%Y-%m-%d")
        mydata = ElementTree.tostring(root)
        if xsd_schema.is_valid(mydata):
            print("The XML instance is valid!")
        else:
            xsd_schema.validate(mydata)
        return mydata


class LongTermMonthlyActivity(models.Model):
    class Meta:
        verbose_name = _("Relevé d'activité mensuel")
        verbose_name_plural = _("Relevés d'activité mensuels")
        unique_together = ('year', 'month', 'patient')

    year = models.PositiveIntegerField(_('Year'))
    # invoice month
    month = models.PositiveIntegerField(_('Month'))
    patient = models.ForeignKey('invoices.Patient', on_delete=models.CASCADE,
                                related_name='longtermmonthlyactivity_patient')
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        return f"{self.year} - {self.month}"


class LongTermMonthlyActivityDetail(models.Model):
    class Meta:
        verbose_name = _("Détail du relevé d'activité mensuel")
        verbose_name_plural = _("Détails des relevés d'activité mensuels")

    long_term_monthly_activity = models.ForeignKey(LongTermMonthlyActivity, on_delete=models.CASCADE,
                                                   related_name='activity_details')
    activity_date = models.DateField(_('Activity Date'))
    activity = models.ForeignKey(LongTermCareItem, on_delete=models.CASCADE, related_name='activity_dtl_to_item')
    quantity = models.PositiveIntegerField(_('Quantity'))

    def __str__(self):
        return f"{self.long_term_monthly_activity} - {self.activity} - {self.quantity}"
