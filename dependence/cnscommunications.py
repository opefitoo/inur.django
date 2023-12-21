import base64
from ftplib import FTP
from io import TextIOWrapper

import lxml.etree as ElementTree
import xmlschema
from constance import config
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dependence.enums.longtermcare_enums import ChangeTypeChoices, UnavailabilityTypeChoices
from invoices.models import Patient
from invoices.notifications import notify_system_via_google_webhook


def generate_xml_using_xmlschema_using_instance(instance):
    # Load the XSD schema file
    xsd_schema = xmlschema.XMLSchema('dependence/xsd/ad-declaration-14.xsd')
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
    DateEnvoiPrestataire.text = instance.provider_date_of_sending.strftime("%Y-%m-%d")
    # create sub element Prestataire
    Prestataire = ElementTree.SubElement(root, "Prestataire")
    Prestataire.text = config.CODE_PRESTATAIRE
    for change in instance.longtermcaredeclaration_to_chg_dec_file.all():
        # create sub element Changement
        Changements = ElementTree.SubElement(root, "Changements")
        # create sub element TypeChangement
        TypeChangement = ElementTree.SubElement(Changements, "TypeChangement")
        if change.change_type == ChangeTypeChoices.ENTRY:
            TypeChangement.text = "ENTREE"
        elif change.change_type == ChangeTypeChoices.EXIT:
            TypeChangement.text = "SORTIE"
        elif change.change_type == ChangeTypeChoices.CORRECTION:
            TypeChangement.text = "CORRECTION"
        # create sub element Reference
        ReferenceChangement = ElementTree.SubElement(Changements, "ReferenceChangement")
        ReferenceChangement.text = change.change_reference
        # create sub element IdentifiantChangementOrganisme
        if change.change_organism_identifier:
            IdentifiantChangementOrganisme = ElementTree.SubElement(Changements, "IdentifiantChangementOrganisme")
            IdentifiantChangementOrganisme.text = change.change_organism_identifier
        # create sub element DateChangement
        PersonneProtegee = ElementTree.SubElement(Changements, "PersonneProtegee")
        PersonneProtegee.text = change.patient.code_sn
        DateChangement = ElementTree.SubElement(Changements, "DateChangement")
        # format date to string 'YYYY-MM-DD'
        DateChangement.text = change.change_date.strftime("%Y-%m-%d")
        # create sub element Information
        Information = ElementTree.SubElement(Changements, "Information")
        Information.text = change.information
    for unavailable in instance.informalcaregiverunavailability_to_chg_dec_file.all():
        # create sub element IndisponibiliteAidant
        IndisponibilitesAidant = ElementTree.SubElement(root, "IndisponibilitesAidant")
        # create sub element TypeIndisponibilite
        TypeIndisponibilite = ElementTree.SubElement(IndisponibilitesAidant, "TypeIndisponibilite")
        if unavailable.unavailability_type == UnavailabilityTypeChoices.DEBUT:
            TypeIndisponibilite.text = "DEBUT"
        elif unavailable.unavailability_type == UnavailabilityTypeChoices.RETOUR:
            TypeIndisponibilite.text = "RETOUR"
        elif unavailable.unavailability_type == UnavailabilityTypeChoices.CORRECTION:
            TypeIndisponibilite.text = "CORRECTION"
        elif unavailable.unavailability_type == UnavailabilityTypeChoices.DEFINITIVE:
            TypeIndisponibilite.text = "DEFINITIVE"
        # create sub element ReferenceIndisponibilite
        ReferenceIndisponibilite = ElementTree.SubElement(IndisponibilitesAidant, "ReferenceIndisponibilite")
        ReferenceIndisponibilite.text = unavailable.unavailability_reference
        # Patient
        PersonneProtegee = ElementTree.SubElement(IndisponibilitesAidant, "PersonneProtegee")
        PersonneProtegee.text = unavailable.patient.code_sn
        # create sub element CodeCNSAidant
        Aidant = ElementTree.SubElement(IndisponibilitesAidant, "Aidant")
        Aidant.text = unavailable.cns_code_of_the_informal_caregiver
        # create sub element DateDebutIndisponibilite
        DateIndisponibilite = ElementTree.SubElement(IndisponibilitesAidant, "DateIndisponibilite")
        DateIndisponibilite.text = unavailable.unavailability_date.strftime("%Y-%m-%d")
    # create a new XML file with the results
    mydata = ElementTree.tostring(root, xml_declaration=True, encoding='UTF-8')
    if not xsd_schema.is_valid(mydata):
        print("The XML instance is valid!")
        raise ValidationError({'generated_xml': [_("The XML file is not valid")]})
    else:
        xsd_schema.validate(mydata)
    return mydata


def long_term_care_declaration_file_path_for_return(instance, filename):
    return f"long_term_care_declaration/{instance.internal_reference}/{filename}"


def long_term_care_declaration_file_path(instance, filename):
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
    newfilename = f"D{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_ASD_DCL_001_{instance.internal_reference}{instance.generated_xml_version}.xml"
    # newfilename, file_extension = os.path.splitext(filename)
    return f"long_term_care_declaration/{instance.internal_reference}/{newfilename}"


class ChangeDeclarationFile(models.Model):
    class Meta:
        ordering = ["provider_date_of_sending"]
        verbose_name = _("Fichier de déclaration de changement")
        verbose_name_plural = _("Fichiers de déclaration de changement")

    # DateEnvoiPrestataire
    provider_date_of_sending = models.DateField(_("Provider date of sending"))
    internal_reference = models.CharField(_("Internal reference"), max_length=10)
    # boolean to force the generation of the xml file
    force_xml_generation = models.BooleanField(_("Force XML generation"),
                                               help_text=_(
                                                   "Force the generation of the XML file, don't forget to check the checkbox before saving the form"),
                                               default=False)
    # boolean to force the generation of the xml file
    force_xml_return_check = models.BooleanField(_("Force XML Retour Check"),
                                               help_text=_(
                                                   "Force the analysis of the XML Retour file, don't forget to check the checkbox before saving the form"),
                                               default=False)
    # generated_xml file
    generated_xml = models.FileField(_("Generated XML"),
                                     upload_to=long_term_care_declaration_file_path, blank=True, null=True)
    manually_generated_xml = models.FileField(_("Manually generated XML"),
                                              upload_to=long_term_care_declaration_file_path, blank=True, null=True)
    # generated_xml_version is an incremental number that is incremented each time the xml is generated, and is readonly
    generated_xml_version = models.IntegerField(_("Generated XML version"), default=0)
    generated_return_xml = models.FileField(_("Retour CNS return XML"),
                                            upload_to=long_term_care_declaration_file_path_for_return, blank=True,
                                            null=True)
    # date time sent to ftp server
    sent_to_ftp_server = models.DateTimeField(_("Sent to FTP server"), blank=True, null=True)
    # send status to ftp server
    send_status_to_ftp_server = models.CharField(_("Send status to FTP server"), max_length=50, blank=True, null=True)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    updates_log = models.TextField(_("Updates log"), blank=True, null=True)

    # internal_reference must be unique
    def clean(self):
        if self.__class__.objects.filter(internal_reference=self.internal_reference).exclude(pk=self.pk).exists():
            raise ValidationError({'internal_reference': [_("Internal reference must be unique")]})


    def generate_xml_using_xmlschema(self):
        # Load the XSD schema file
        xsd_schema = xmlschema.XMLSchema('dependence/xsd/ad-declaration-14.xsd')
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
        for unavailability in self.link_to_chg_dec_file.all():
            # create sub element Changement
            IndisponibilitesAidant = ElementTree.SubElement(root, "IndisponibilitesAidant")
            # create sub element TypeChangement
            TypeIndisponibilite = ElementTree.SubElement(IndisponibilitesAidant, "TypeIndisponibilite")
            if unavailability.change_type == ChangeTypeChoices.ENTRY:
                TypeIndisponibilite.text = "ENTREE"
            elif unavailability.change_type == ChangeTypeChoices.EXIT:
                TypeIndisponibilite.text = "SORTIE"
            elif unavailability.change_type == ChangeTypeChoices.CORRECTION:
                TypeIndisponibilite.text = "CORRECTION"
            # create sub element ReferenceIndisponibilite
            ReferenceIndisponibilite = ElementTree.SubElement(IndisponibilitesAidant, "ReferenceIndisponibilite")
            ReferenceIndisponibilite.text = unavailability.unavailability_reference
            if unavailability.change_organism_identifier:
                # create sub element IdentifiantChangementOrganisme
                IdentifiantIndisponibiliteOrganis = ElementTree.SubElement(IndisponibilitesAidant,
                                                                        "IdentifiantIndisponibiliteOrganis")
                IdentifiantIndisponibiliteOrganis.text = unavailability.change_organism_identifier
            # create sub element PersonneProtegee
            PersonneProtegee = ElementTree.SubElement(IndisponibilitesAidant, "PersonneProtegee")
            PersonneProtegee.text = unavailability.patient.code_sn
            # create sub element Aidant
            Aidant = ElementTree.SubElement(IndisponibilitesAidant, "Aidant")
            Aidant.text = unavailability.patient.informal_caregiver.code_sn
            # create sub element DateIndisponibilite
            DateIndisponibilite = ElementTree.SubElement(IndisponibilitesAidant, "DateIndisponibilite")
            # format date to string 'YYYY-MM-DD'
            DateIndisponibilite.text = unavailability.unavailability_date.strftime("%Y-%m-%d")


        # create a new XML file with the results
        mydata = ElementTree.tostring(root, xml_declaration=True, encoding='UTF-8')
        if xsd_schema.is_valid(mydata):
            print("The XML instance is valid!")
        else:
            xsd_schema.validate(mydata)
        return mydata

    def __str__(self):
        # take only last part of the path to the file
        if self.generated_xml:
            filename = self.generated_xml.name.split('/')[-1]
            return "Echanges électroniques envoyés le %s ref. %s (%s)" % (self.provider_date_of_sending,
                                                                          self.internal_reference,
                                                                          filename)
        else:
            return "Echanges électroniques envoyés le %s ref. %s" % (self.provider_date_of_sending,
                                                                     self.internal_reference)

    def send_xml_to_ftp(self):
        try:
            # connect to the ftp server
            ftp = FTP(config.FTP_HOST)
            # print("FTP connection closed, password was: %s" % base64.b64decode(config.FTP_PASSWORD).decode("utf-8"))
            ftp.login(user=config.FTP_USER, passwd=base64.b64decode(config.FTP_PASSWORD).decode("utf-8"))
            # change directory to the one containing the xml files
            ftp.cwd(config.FTP_XML_DIRECTORY)
            # send the xml file but remember that this backend doesn't support absolute paths.
            # So you can't use os.path.join here.
            # the file looks like 'long_term_care_declaration/HC002/D30249751202303_ASD_DCL_001_HC002.xml' but we don't need the
            # first part of the path
            file_name = self.generated_xml.name.split('/')[-1]
            ftp.storbinary('STOR %s' % file_name, self.generated_xml)
            # close the connection
            # password is base64 encoded, decode it before printing
            ftp.quit()
        except Exception as e:
            self.send_status_to_ftp_server = e


class DeclarationDetail(models.Model):
    link_to_chg_dec_file = models.ForeignKey(
        ChangeDeclarationFile,
        help_text=_("Link to the file containing the declaration of change"),
        related_name="longtermcaredeclaration_to_chg_dec_file",
        on_delete=models.CASCADE,
    )
    patient = models.ForeignKey(
        Patient,
        help_text=_(
            "Only looks for patients covered by long-term care insurance, check that the checkbox is validated if you cannot find your patient"),
        related_name="declaration_dtl_to_patient",
        on_delete=models.CASCADE,
        limit_choices_to={"is_under_dependence_insurance": True},
    )
    # Année de décompte
    year_of_count = models.IntegerField(_("Year of count"))
    # Mois de décompte
    month_of_count = models.IntegerField(_("Month of count"))
    change_type = models.CharField(_("Change type"), max_length=10, choices=ChangeTypeChoices.choices)
    change_reference = models.CharField(_("Change reference"), max_length=50,
                                        help_text=_(
                                            "Le prestataire est libre de choisir son système de référencement des déclarations"))
    # IdentifiantChangementOrganisme
    change_organism_identifier = models.CharField(_("Change organism identifier"), max_length=50, blank=True, null=True,
                                                  help_text=_("Correspond à la référence donnée à la déclaration par "
                                                              "l’organisme gestionnaire. Celui-ci sera renseigné dans le"
                                                              " fichier retour. Ce champ doit obligatoirement être "
                                                              "renseigné lors d’une déclaration de correction."))
    # DateChangement
    change_date = models.DateField(_("Change date"), default=timezone.now
                                   , help_text=_("Date d’entrée ou de sortie indiquant le jour, le mois et l’année."))
    # Information
    information = models.TextField(_("Information"), max_length=50,
                                   help_text=_("Ce champ est optionnel et peut contenir du texte libre."))
    # AnomalieChangement
    change_anomaly = models.TextField(_("Change anomaly"), max_length=80, blank=True, null=True,
                                      help_text=_("Ce champ est optionnel et peut contenir du texte libre."))

    # validate unicity of the combination of patient, change_reference
    class Meta:
        unique_together = ('patient', 'change_reference')
        verbose_name = _("Déclarations assurance dépendance")
        verbose_name_plural = _("Déclarations assurance dépendance")

    def __str__(self):
        return f"Patient {self.patient} - {self.change_type} - {self.change_reference} - {self.change_date}"

    # also validate model fields
    def clean(self):
        # look for previous changes with the same reference and same patient but different id
        previous_change = DeclarationDetail.objects.filter(
            patient=self.patient,
            change_reference=self.change_reference,
        ).exclude(id=self.id).first()
        if previous_change:
            # throw error mentioning the id of the previous change and also the id of link_to_chg_dec_file
            raise ValidationError(
                _("A change with the same reference already exists for this patient. "
                  "The id of the previous change is %(previous_change_id)s and the id of the file containing the "
                  "previous change is %(previous_change_file_id)s"),
                code='invalid',
                params={'previous_change_id': previous_change.id,
                        'previous_change_file_id': previous_change.link_to_chg_dec_file},
            )


# class that represents the unavailability of the informal caregiver
class InformalCaregiverUnavailability(models.Model):
    class Meta:
        verbose_name = _("Indisponibilité aidant")
        verbose_name_plural = _("Indisponibilités aidant")

    patient = models.ForeignKey(
        Patient,
        help_text=_(
            "Only looks for patients covered by long-term care insurance, check that the checkbox is validated if you cannot find your patient"),
        related_name="informalcaregiverunavailability_to_patient",
        on_delete=models.CASCADE,
        limit_choices_to={"is_under_dependence_insurance": True},
    )

    # Date début indisponibilité
    unavailability_date = models.DateField(_("Unavailable date"), default=timezone.now)
    # unavailability_type can be "DEBUT" or "FIN"
    unavailability_type = models.CharField(_("Unavailable type"), max_length=10,
                                           choices=UnavailabilityTypeChoices.choices)
    unavailability_reference = models.CharField(_("Unavailable reference"), max_length=50,
                                                help_text=_(
                                                    "Le prestataire est libre de choisir son système de référencement des déclarations"))
    unavailability_organism_identifier = models.CharField(_("Unavailable organism identifier"), max_length=50,
                                                            blank=True, null=True,
                                                            help_text=_("Correspond à la référence donnée à la déclaration par "
                                                                        "l’organisme gestionnaire. Celui-ci sera renseigné dans le"
                                                                        " fichier retour. Ce champ doit obligatoirement être "
                                                                        "renseigné lors d’une déclaration de correction."))
    cns_code_of_the_informal_caregiver = models.CharField(_("CNS code of the informal caregiver"), max_length=50,
                                                          help_text=_(
                                                              "Code CNS de l’aidant. Ce champ est obligatoire."))

    # Lien avec la déclaration de changement
    link_unav_to_chg_dec_file = models.ForeignKey(
        ChangeDeclarationFile,
        help_text=_("Link to the file containing the declaration of change"),
        related_name="informalcaregiverunavailability_to_chg_dec_file",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"Indisponibilité aidant du {self.unavailability_date} type {self.unavailability_type} ref {self.unavailability_reference}"
def treat_xml_return_check(instance):
    if instance.generated_return_xml:
        xsd_schema = xmlschema.XMLSchema('dependence/xsd/ad-declaration-14.xsd')

        # if self.generated_return_xml name is emtpy, then the file has not been generated yet
        if instance.generated_return_xml.name and instance.generated_return_xml.name != '':
            with instance.generated_return_xml as return_file:
                read_file = TextIOWrapper(return_file, encoding='UTF-8')
                xml_data = return_file.read()
                xsd_schema.validate(xml_data)
                # Get the data from the XML file
                xml_data = xsd_schema.to_dict(xml_data)
                # Here use detach
                read_file.detach()
                # xml_file = self.generated_return_xml
                # xml_file.open()
                # xml_data = xml_file.read()
                # xml_file.close()
                # xsd_schema.validate(xml_data)
                # Get the data from the XML file
                # xml_data = xsd_schema.to_dict(xml_data)
                if xml_data['Type']['Type'] == 'RETDCL':
                    for changement in xml_data['Changements']:
                        print(changement)
                        identifiant_changement_organisme = changement['IdentifiantChangementOrganisme']
                        declaration_changes = DeclarationDetail.objects.filter(
                            change_reference=changement['ReferenceChangement'],
                            patient__code_sn=changement['PersonneProtegee'])
                        if declaration_changes:
                            for declaration_change in declaration_changes:
                                if changement.get('AnomalieChangement'):
                                    for anomaly in changement['AnomalieChangement']:
                                        change_anomaly_string = f"{anomaly['type']} Code : {anomaly['code']} Motif : {anomaly['motif']}"
                                        if declaration_change.change_anomaly != change_anomaly_string:
                                            declaration_change.change_anomaly = change_anomaly_string
                                            if instance.updates_log:
                                                instance.updates_log += f"{declaration_change.change_anomaly} Fait le {timezone.now()}\n"
                                            else:
                                                instance.updates_log = f"{declaration_change.change_anomaly} Fait le {timezone.now()}\n"
                                if declaration_change.change_organism_identifier != identifiant_changement_organisme:
                                    declaration_change.change_organism_identifier = identifiant_changement_organisme
                                    # previous value of change can be None then we need to display as "Not set" in the logs
                                    if declaration_change.change_organism_identifier:
                                        previous_value = declaration_change.change_organism_identifier
                                    else:
                                        previous_value = "Not set"
                                    if instance.updates_log:
                                        instance.updates_log += f"Changement from {previous_value} to {identifiant_changement_organisme} on {declaration_change} Fait le {timezone.now()}\n"
                                    else:
                                        instance.updates_log = f"Changement from {previous_value} to {identifiant_changement_organisme} on {declaration_change} Fait le {timezone.now()}\n"
                                declaration_change.save()
                        else:
                            for anomaly in changement['AnomalieChangement']:
                                change_anomaly_string = f"{anomaly['type']} Code : {anomaly['code']} Motif : {anomaly['motif']}"
                                if instance.updates_log:
                                    instance.updates_log += f"{change_anomaly_string} Fait le {timezone.now()}\n"
                                else:
                                    instance.updates_log = f"{change_anomaly_string} Fait le {timezone.now()}\n"
                else:
                    raise ValidationError({'generated_return_xml': [_("The XML file is not a return file")]})
        # notify via chat
        message = f"Le fichier de retour de changement {instance} a été traité avec succès. Date heure : {timezone.now()}"
        notify_system_via_google_webhook(message)

@receiver(pre_save, sender=ChangeDeclarationFile, dispatch_uid="generate_xml_file_and_notify_via_chat")
def generate_xml_file_and_notify_via_chat(sender, instance, **kwargs):
    if instance.force_xml_return_check:
        treat_xml_return_check(instance)
        instance.force_xml_return_check = False 
    if not instance.force_xml_generation:
        return
    message = f"Le fichier de déclaration de changement {instance} a été généré avec succès. Date heure : {timezone.now()}"
    try:
        # generate the xml file
        xml = generate_xml_using_xmlschema_using_instance(instance)
        # update the xml field
        content_file = ContentFile(xml, name='long_term_care_declaration.xml')
        instance.generated_xml = content_file
        instance.generated_xml_version += 1
    except Exception as e:
        message = f"Le fichier de déclaration de changement {instance} n'a pas pu être généré. Erreur : {e}. Date heure : {timezone.now()}"
        notify_system_via_google_webhook(message)
        print(e)
    finally:
        notify_system_via_google_webhook(message)
        instance.force_xml_generation = False
