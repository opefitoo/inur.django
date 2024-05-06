import hashlib

from constance import config
from gps_tracker import Client, Config

from invoices.enums.generic import BatchTypeChoices


def encode_payment_reference(str_to_encode):
    return int(hashlib.sha1(str_to_encode.encode("utf-8")).hexdigest(), 16) % (10 ** 8)


def decode_payment_reference(hash_to_decode):
    return hashlib.sha1(hash_to_decode.decode("utf-8"))


def invoxia_position_and_battery(invoxia_identifier: str):
    # if not self.is_connected_to_invoxia:
    #     return "n/a"
    # if self.is_connected_to_invoxia and not self.invoxia_identifier:
    #     return "n/a Error: invoxia id is not set"
    invoxia_client = Client(config=Config(
        username=config.INVOXIA_USERNAME,
        password=config.INVOXIA_PASSWORD,
    ))
    trackers = invoxia_client.get_trackers()
    # get position of tracker with id invoxia_identifier
    for tracker in trackers:
        if tracker.id == int(invoxia_identifier):
            return invoxia_client.get_locations(device=tracker, max_count=1)[0], invoxia_client.get_tracker_status(
                device=tracker).battery
    return None


def invoice_itembatch_prefac_filename(instance, filename):
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
    month_of_count = f"{instance.end_date.month:02d}"
    year_of_count = f"{instance.end_date.year:04d}"
    if instance.id:
        reference_interne = f"{instance.id:04d}{instance.version:03d}"
    else:
        reference_interne = "0000"
    # loop swtich on BatchTypeChoices to build filename
    if instance.batch_type == BatchTypeChoices.CNS_INF:
        legal_frame = "INF"
    elif instance.batch_type == BatchTypeChoices.CNS_PAL:
        legal_frame = "PAL"
    else:
        legal_frame = "XXX"
    newfilename = f"F{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_{legal_frame}_PREFAC_001_{reference_interne}"
    # newfilename, file_extension = os.path.splitext(filename)
    return f"inf_invoices/{instance.end_date.year}/{instance.end_date.month}/{newfilename}"


def invoice_itembatch_medical_prescription_filename(instance, filename):
    month_of_count = f"{instance.end_date.month:02d}"
    year_of_count = f"{instance.end_date.year:04d}"
    if instance.id:
        reference_interne = f"{instance.id:04d}{instance.version:03d}"
    else:
        reference_interne = "0000"
    newfilename = f"F{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_FACTURE_{reference_interne}.pdf"
    # newfilename, file_extension = os.path.splitext(filename)
    return f"inf_invoices/{instance.end_date.year}/{instance.end_date.month}/{newfilename}"

def invoice_itembatch_12_pct_filename(instance, filename):
    month_of_count = f"{instance.end_date.month:02d}"
    year_of_count = f"{instance.end_date.year:04d}"
    if instance.id:
        reference_interne = f"{instance.id:04d}{instance.version:03d}"
    else:
        reference_interne = "0000"
    newfilename = f"F{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_FACTURE_12_PCT_{reference_interne}.pdf"
    # newfilename, file_extension = os.path.splitext(filename)
    return f"inf_invoices/{instance.end_date.year}/{instance.end_date.month}/{newfilename}"


def invoice_itembatch_ordo_filename(instance, filename):
    month_of_count = f"{instance.end_date.month:02d}"
    year_of_count = f"{instance.end_date.year:04d}"
    if instance.id:
        reference_interne = f"{instance.id:04d}{instance.version:03d}"
    else:
        reference_interne = "0000"
    newfilename = f"F{config.CODE_PRESTATAIRE}{year_of_count}{month_of_count}_ordo_{reference_interne}.pdf"
    # newfilename, file_extension = os.path.splitext(filename)
    return f"inf_invoices/{instance.end_date.year}/{instance.end_date.month}/{newfilename}"


def update_bedsore_pictures_filenames(instance, filename):
    # instance is a BedSorePicture object
    # filename is the original filename
    return "bedsores/" + instance.bedsore.patient.name + "/" + filename
