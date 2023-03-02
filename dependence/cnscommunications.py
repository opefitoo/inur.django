import lxml.etree as ElementTree
import xmlschema
from constance import config
from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dependence.enums.longtermcare_enums import ChangeTypeChoices
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
            IdentifiantChangementOrganisme.text = change['change_organism_identifier']
        # create sub element DateChangement
        PersonneProtegee = ElementTree.SubElement(Changements, "PersonneProtegee")
        PersonneProtegee.text = change.patient.code_sn
        DateChangement = ElementTree.SubElement(Changements, "DateChangement")
        # format date to string 'YYYY-MM-DD'
        DateChangement.text = change.change_date.strftime("%Y-%m-%d")
        # create sub element Information
        Information = ElementTree.SubElement(Changements, "Information")
        Information.text = change.information
    # create a new XML file with the results
    mydata = ElementTree.tostring(root)
    if xsd_schema.is_valid(mydata):
        print("The XML instance is valid!")
    else:
        xsd_schema.validate(mydata)
    return mydata

def generate_xml_using_xmlschema(cleaned_data, inlines_cleaned_data):
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
    DateEnvoiPrestataire.text = cleaned_data['provider_date_of_sending'].strftime("%Y-%m-%d")
    # create sub element Prestataire
    Prestataire = ElementTree.SubElement(root, "Prestataire")
    Prestataire.text = config.CODE_PRESTATAIRE
    for change in inlines_cleaned_data:
        # create sub element Changement
        Changements = ElementTree.SubElement(root, "Changements")
        # create sub element TypeChangement
        TypeChangement = ElementTree.SubElement(Changements, "TypeChangement")
        if change['change_type'] == ChangeTypeChoices.ENTRY:
            TypeChangement.text = "ENTREE"
        elif change['change_type'] == ChangeTypeChoices.EXIT:
            TypeChangement.text = "SORTIE"
        elif change['change_type'] == ChangeTypeChoices.CORRECTION:
            TypeChangement.text = "CORRECTION"
        # create sub element Reference
        ReferenceChangement = ElementTree.SubElement(Changements, "ReferenceChangement")
        ReferenceChangement.text = change['change_reference']
        # create sub element IdentifiantChangementOrganisme
        if change['change_organism_identifier']:
            IdentifiantChangementOrganisme = ElementTree.SubElement(Changements, "IdentifiantChangementOrganisme")
            IdentifiantChangementOrganisme.text = change['change_organism_identifier']
        # create sub element DateChangement
        PersonneProtegee = ElementTree.SubElement(Changements, "PersonneProtegee")
        PersonneProtegee.text = change['patient'].code_sn
        DateChangement = ElementTree.SubElement(Changements, "DateChangement")
        # format date to string 'YYYY-MM-DD'
        DateChangement.text = change['change_date'].strftime("%Y-%m-%d")
        # create sub element Information
        Information = ElementTree.SubElement(Changements, "Information")
        Information.text = change['information']
    # create a new XML file with the results
    mydata = ElementTree.tostring(root)
    if xsd_schema.is_valid(mydata):
        print("The XML instance is valid!")
    else:
        xsd_schema.validate(mydata)
    return mydata

def long_term_care_declaration_file_path_for_return(instance, filename):
    return f"long_term_care_declaration/{instance.link_to_long_term_care.patient.code_sn}/{filename}"


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
    newfilename = f"D{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_ASD_DCL_001_{instance.internal_reference}.xml"
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
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        # increment the version number, only if data has changed and the object is not new
        if self.pk:
            self.generated_xml_version += 1
        # also generate the xml file
        #data = self.generate_xml_using_xmlschema()
        #self.generated_xml = ContentFile(data, name='long_term_care_declaration.xml')
        super().save(force_insert, force_update, using, update_fields)

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
        for change in self.link_to_chg_dec_file.all():
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
            ReferenceChangement.text = change['change_reference']
            # create sub element IdentifiantChangementOrganisme
            if change['change_organism_identifier']:
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
        # create a new XML file with the results
        mydata = ElementTree.tostring(root)
        if xsd_schema.is_valid(mydata):
            print("The XML instance is valid!")
        else:
            xsd_schema.validate(mydata)
        return mydata

    def __str__(self):
        return "Echanges électroniques envoyés le %s" % self.provider_date_of_sending

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
        related_name="longtermcare_to_patient",
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


@receiver(pre_save, sender=ChangeDeclarationFile, dispatch_uid="generate_xml_file_and_notify_via_chat")
def generate_xml_file_and_notify_via_chat(sender, instance, **kwargs):
    message = f"Le fichier de déclaration de changement {instance} a été généré avec succès."
    try:
        # generate the xml file
        xml = generate_xml_using_xmlschema_using_instance(instance)
        # update the xml field
        content_file = ContentFile(xml, name='long_term_care_declaration.xml')
        instance.generated_xml = content_file
    except Exception as e:
        message = f"Le fichier de déclaration de changement {instance} n'a pas pu être généré."
        notify_system_via_google_webhook(message)
        print(e)
    finally:
        notify_system_via_google_webhook(message)

