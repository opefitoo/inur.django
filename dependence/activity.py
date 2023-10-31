import calendar
import datetime
import os

import lxml.etree as ElementTree
import xmlschema
from constance import config
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from dependence.longtermcareitem import LongTermCareItem


def long_term_care_activity_declaration_file_path(instance, filename):
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
    month_of_count = f"{instance.provider_date_of_sending.month:02d}"
    year_of_count = f"{instance.provider_date_of_sending.year:04d}"
    newfilename = f"D{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_ASD_DCL_001_{instance.id}{instance.version_number}.xml"
    # newfilename, file_extension = os.path.splitext(filename)
    return f"long_term_monthly_activity_declaration/{instance.id}/{newfilename}"


class LongTermMonthlyActivityFile(models.Model):
    class Meta:
        verbose_name = _("Fichier d'activité mensuel")
        verbose_name_plural = _("Fichiers d'activité mensuels")

    year = models.PositiveIntegerField(_('Year'))
    # invoice month
    month = models.PositiveIntegerField(_('Month'))
    provider_date_of_sending = models.DateField(_('Provider Date of Sending'))
    force_creation = models.BooleanField(_('Force Creation'), default=False)
    file = models.FileField(upload_to=long_term_care_activity_declaration_file_path,
                            verbose_name=_("File"), blank=True, null=True)
    version_number = models.PositiveIntegerField(_('Version Number'))
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    # link to the LongTermMonthlyActivity model
    monthly_activities = models.ManyToManyField('LongTermMonthlyActivity',
                                                verbose_name=_("Activities"),
                                                help_text=_(
                                                    "Please first save year and month to be able to add activities"),
                                                blank=True)

    def __str__(self):
        return f"{self.file.name}"

    def save(self, *args, **kwargs):
        # if self.force_creation:
        #     self.file.delete(save=False)
        #     self.file = None
        if self.force_creation and self.year and self.month:
            self.version_number += 1
            # generate xml data
            xml_data = self.generate_xml_using_xmlschema()
            if xml_data:
                # create file
                content_file = ContentFile(xml_data, name='long_term_care_activity.xml')
                self.file = content_file
                self.force_xml_generation = False
        super().save(*args, **kwargs)

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
            # group by activity date
            dtls_grouped_by_activity_date = LongTermMonthlyActivityDetail.objects.filter(
                long_term_monthly_activity=activity).values('activity_date').annotate(
                count=Count('activity_date')).order_by('activity_date')
            # dtls = LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=activity).all()

            for dtl in dtls_grouped_by_activity_date:
                Activite = ElementTree.SubElement(Activites, "Activite")
                AevTypeActivite = ElementTree.SubElement(Activite, "TypeActivite")
                AevTypeActivite.text = "AEV"
                # DateActivite
                DateActivite = ElementTree.SubElement(Activite, "DateActivite")
                DateActivite.text = dtl['activity_date'].strftime("%Y-%m-%d")
        mydata = ElementTree.tostring(root, xml_declaration=True, encoding='UTF-8')
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

    @property
    def ratio_days_on_days_of_month(self):
        days_in_month = calendar.monthrange(self.year, self.month)[1]
        # number of LongTermMonthlyActivityDetail grouped by activity_date
        count = LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=self).values('activity_date').annotate(
            count=Count('activity_date')).count()
        return "%s / %s" % (count, days_in_month)

    def get_first_date_for_activity_detail(self):
        # get first LongTermMonthlyActivityDetail by activity_date
        return LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=self).values('activity_date').annotate(
            count=Count('activity_date')).order_by('activity_date').first()['activity_date']

    def get_last_date_for_activity_detail(self):
        # get first LongTermMonthlyActivityDetail by activity_date
        return LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=self).values('activity_date').annotate(
            count=Count('activity_date')).order_by('activity_date').last()['activity_date']

    def how_many_occurrence_of_activity(self, activity, start_date, end_date):
        return LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=self, activity=activity,
                                                            activity_date__gte=start_date,
                                                            activity_date__lte=end_date).count()
    def duplicate_for_next_month(self):
        # get last month
        last_month = self.month
        last_year = self.year
        if self.month == 12:
            new_month = 1
            new_year = self.year + 1
        else:
            new_month = self.month + 1
            new_year = self.year
        # get last month activity
        last_month_activity = LongTermMonthlyActivity.objects.filter(patient=self.patient, month=last_month,
                                                                     year=last_year).first()
        # get last month activity details
        last_month_activity_details = LongTermMonthlyActivityDetail.objects.filter(
            long_term_monthly_activity=last_month_activity).all()
        # create new activity
        new_activity = LongTermMonthlyActivity.objects.create(year=new_year, month=new_month, patient=self.patient)
        # determine last day of the month
        last_day_num = calendar.monthrange(new_year, new_month)[1]
        last_day_of_last_month = calendar.monthrange(last_year, last_month)[1]
        last_day_date = datetime.date(new_year, new_month, last_day_num)
        # create new activity details
        for activity_dtl_instance in last_month_activity_details:
            how_many_occurrence = self.how_many_occurrence_of_activity(activity_dtl_instance.activity,
                                                 # first day of previous month
                                                    activity_dtl_instance.activity_date.replace(day=1),
                                                    # last day of previous month
                                                    activity_dtl_instance.activity_date.replace(day=last_day_of_last_month))
            # if occurence equals number of days of previous month
            if how_many_occurrence == last_day_of_last_month:
                # create a new activity details for each day of the month
                for day in range(1, last_day_num + 1):
                    new_activity_dtl = LongTermMonthlyActivityDetail(
                        activity_date=datetime.date(new_year, new_month, day),
                        activity=activity_dtl_instance.activity,
                        quantity=activity_dtl_instance.quantity,
                        long_term_monthly_activity=new_activity)
                    new_activity_dtl.save()

    def __str__(self):
        return f"{self.patient} {self.year} - {self.month}"


class LongTermMonthlyActivityDetail(models.Model):
    class Meta:
        verbose_name = _("Détail du relevé d'activité mensuel")
        verbose_name_plural = _("Détails des relevés d'activité mensuels")
        ordering = ['activity_date']

    long_term_monthly_activity = models.ForeignKey(LongTermMonthlyActivity, on_delete=models.CASCADE,
                                                   related_name='activity_details')
    activity_date = models.DateField(_('Activity Date'))
    activity = models.ForeignKey(LongTermCareItem, on_delete=models.CASCADE, related_name='activity_dtl_to_item')
    quantity = models.DecimalField(_('Quantity'), max_digits=5, decimal_places=2)

    def did_activity_happen(self, date, patient):
        if self.activity_date == date and self.long_term_monthly_activity.patient == patient:
            return True
        else:
            return False

    def __str__(self):
        return f"{self.long_term_monthly_activity} - {self.activity} - {self.quantity}"
