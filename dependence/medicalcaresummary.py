import xmlschema
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.datetime_safe import datetime
from django.utils.translation import gettext_lazy as _

from dependence.detailedcareplan import MedicalCareSummaryPerPatient, MedicalCareSummaryPerPatientDetail, \
    SharedMedicalCareSummaryPerPatientDetail
from dependence.longtermcareitem import LongTermCareItem
from invoices.models import Patient
from invoices.notifications import notify_system_via_google_webhook


def file_path_for_spc(instance, filename):
    return f"spc/{filename}"


class MedicalCareSummary(models.Model):
    class Meta:
        verbose_name = _("Synthèse de prise en charge de la CNS")
        verbose_name_plural = _("Synthèses de prise en charge de la CNS")
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    parsing_date = models.DateTimeField("Date de parsing", blank=True,
                                        null=True)

    # Fields
    force_update = models.BooleanField(_("Forcer la mise à jour"), default=False)
    generated_return_xml = models.FileField(_("Fichier CNS SPC"),
                                            upload_to=file_path_for_spc, blank=True,
                                            null=True)
    count_of_supported_persons = models.IntegerField(_("Nombre de personnes prises en charge"), blank=True, null=True)
    # DateEnvoiPrestataire
    date_of_submission = models.DateField(_("Date d'envoi du fichier"), blank=True, null=True)

    def __str__(self):
        return "Synthèse de prise en charge du {0}".format(self.date_of_submission)


def parse_xml_using_xmlschema(instance):
    # Load the XSD schema file
    xsd_schema = xmlschema.XMLSchema('dependence/xsd/ad-synthesepriseencharge-20.xsd')
    # parse the XML file using the schema
    xml_file = instance.generated_return_xml
    xml_file.open()
    xml_data = xml_file.read()
    xml_file.close()
    xsd_schema.validate(xml_data)
    # Get the data from the XML file
    xml_data = xsd_schema.to_dict(xml_data)
    # Get the data from the XML file
    instance.count_of_supported_persons = xml_data['NbPriseEnCharges']
    instance.date_of_submission = xml_data['DateEnvoiPrestataire']
    # get DateEnvoiPrestataire
    # instance.date_of_notification_to_provider = datetime.strptime(xml_data['DateEnvoiPrestataire'], '%Y-%m-%d')
    instance.parsing_date = datetime.now()
    instance.force_update = False
    # loop through PriseEnCharge elements
    for prise_en_charge in xml_data['PriseEnCharge']:
        # print(prise_en_charge['Partage'])
        patient = Patient.objects.get(code_sn=prise_en_charge['Patient'])
        # get DateDemande
        date_of_request = datetime.strptime(prise_en_charge['DateDemande'], '%Y-%m-%d')
        # get Referent
        referent = prise_en_charge['Referent']
        # get DateEvaluation
        date_of_evaluation = datetime.strptime(prise_en_charge['DateEvaluation'], '%Y-%m-%d')
        # get date_of_notification
        date_of_notification = datetime.strptime(prise_en_charge['DateNotification'], '%Y-%m-%d')
        # get plan_number
        plan_number = prise_en_charge['NoPlan']
        # get NoDecision
        decision_number = prise_en_charge['NoDecision']
        # get level_of_needs
        level_of_needs = prise_en_charge['Decision']['Accord']['NiveauBesoins']
        # get start_of_support
        start_of_support = datetime.strptime(prise_en_charge['Decision']['Accord']['DebutPriseEnCharge'], '%Y-%m-%d')
        # get DateDecision
        date_of_decision = datetime.strptime(prise_en_charge['Decision']['Accord']['DateDecision'], '%Y-%m-%d')
        date_of_notification_to_provider = datetime.strptime(xml_data['DateEnvoiPrestataire'], '%Y-%m-%d')
        # get FinPriseEnCharge if key FinPriseEnCharge exists
        end_of_support = None
        if prise_en_charge['Decision']['Accord'].get('FinPriseEnCharge'):
            end_of_support = datetime.strptime(prise_en_charge['Decision']['Accord']['FinPriseEnCharge'], '%Y-%m-%d')
        # get special_package if exists
        special_package = None
        if prise_en_charge['Decision']['Accord'].get('ForfaitSpecial'):
            special_package = prise_en_charge['Decision']['Accord']['ForfaitSpecial']
        # get nature_package if exists
        nature_package = None
        if prise_en_charge['Decision']['Accord'].get('ForfaitPN'):
            nature_package = prise_en_charge['Decision']['Accord']['ForfaitPN']
        # get cash_package if exists
        cash_package = None
        if prise_en_charge['Decision']['Accord'].get('ForfaitPE'):
            cash_package = prise_en_charge['Decision']['Accord']['ForfaitPE']
        # get fmi_right which is a boolean if 'O' is True else False
        fmi_right = True if prise_en_charge['DroitFMI'] == 'O' else False
        plan_par_patient = MedicalCareSummaryPerPatient.objects.create(
            patient=patient,
            date_of_request=date_of_request,
            referent=referent,
            date_of_evaluation=date_of_evaluation,
            date_of_notification=date_of_notification,
            plan_number=plan_number,
            decision_number=decision_number,
            date_of_notification_to_provider=date_of_notification_to_provider,
            level_of_needs=level_of_needs,
            start_of_support=start_of_support,
            date_of_decision=date_of_decision,
            end_of_support=end_of_support,
            special_package=special_package,
            nature_package=nature_package,
            cash_package=cash_package,
            fmi_right=fmi_right,
        )
        if prise_en_charge.get('Descriptions'):
            for act in prise_en_charge['Descriptions']:
                if not LongTermCareItem.objects.filter(code__exact=act['CodeActe']).exists():
                    LongTermCareItem.objects.get_or_create(
                        code=act['CodeActe'],
                        description=act['Description'],
                    )
        # print(prise_en_charge['Partage'])
        if prise_en_charge.get('Partage') is None:
            for prestations in prise_en_charge['Prestatations']:
                # if periodicity is 'SEMAINE' then it is WEEKLY elif 'ANNEE' then it is YEARLY else throw an error
                periodicity = None
                if prestations['Frequence']['Periodicite'] == 'SEMAINE':
                    periodicity = 'W'
                elif prestations['Frequence']['Periodicite'] == 'ANNEE':
                    periodicity = 'Y'
                else:
                    raise Exception("Periodicity is not valid")
                MedicalCareSummaryPerPatientDetail.objects.create(
                    item=LongTermCareItem.objects.get(code__exact=prestations['CodeActe']),
                    medical_care_summary_per_patient=plan_par_patient,
                    number_of_care=prestations['Frequence']['Nombre'],
                    # if periodicity is 'SEMAINE' then it is WEEKLY elif 'ANNEE' then it is YEARLY else throw an error
                    periodicity=periodicity,

                )
        else:
            for prestations in prise_en_charge['Partage']['PrestationsPrestataire']:
                # if periodicity is 'SEMAINE' then it is WEEKLY elif 'ANNEE' then it is YEARLY else throw an error
                periodicity = None
                if prestations['Frequence']['Periodicite'] == 'SEMAINE':
                    periodicity = 'W'
                elif prestations['Frequence']['Periodicite'] == 'ANNEE':
                    periodicity = 'Y'
                else:
                    raise Exception("Periodicity is not valid")
                MedicalCareSummaryPerPatientDetail.objects.create(
                    item=LongTermCareItem.objects.get(code__exact=prestations['CodeActe']),
                    medical_care_summary_per_patient=plan_par_patient,
                    number_of_care=prestations['Frequence']['Nombre'],
                    # if periodicity is 'SEMAINE' then it is WEEKLY elif 'ANNEE' then it is YEARLY else throw an error
                    periodicity=periodicity,

                )
            plan_par_patient.sn_code_aidant = prise_en_charge['Partage']['Aidant']
            plan_par_patient.save()
            if prise_en_charge['Partage'].get('PrestationsAidant'):
                for prestations in prise_en_charge['Partage']['PrestationsAidant']:
                    periodicity_partage = None
                    if prestations['Frequence']['Periodicite'] == 'SEMAINE':
                        periodicity_partage = 'W'
                    elif prestations['Frequence']['Periodicite'] == 'ANNEE':
                        periodicity_partage = 'Y'
                    else:
                        raise Exception("Periodicity is not valid %s" % prestations['Frequence']['Periodicite'])
                    SharedMedicalCareSummaryPerPatientDetail.objects.create(
                        item=LongTermCareItem.objects.get(code__exact=prestations['CodeActe']),
                        medical_care_summary_per_patient=plan_par_patient,
                        number_of_care=prestations['Frequence']['Nombre'],
                        periodicity=periodicity_partage,
                    )
    instance.save()


@receiver(post_save, sender=MedicalCareSummary, dispatch_uid="medicalcare_parse_xml_file_and_notify_via_chat_gsfQyUJw")
def parse_xml_and_notify_via_chat(sender, instance, **kwargs):
    message = "Le fichier de synthèse de prise en charge %s a été mis à jour." % instance.generated_return_xml
    if instance.force_update:
        parse_xml_using_xmlschema(instance)
        notify_system_via_google_webhook(message)
        return
