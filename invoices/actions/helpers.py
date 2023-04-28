import hashlib
from typing import List

from constance import config
from gps_tracker import Client, Config

from invoices.models import PaymentReference


def encode_payment_reference(str_to_encode):
    return int(hashlib.sha1(str_to_encode.encode("utf-8")).hexdigest(), 16) % (10 ** 8)


def generate_payment_reference(invoice_numbers: List[int]):
    from datetime import datetime
    today = datetime.today()
    invoice_list = [n for n in invoice_numbers]
    p = PaymentReference(invoice_list=invoice_list)
    p.save()
    return "%s%s%s-%s-%s" % (today.year, today.month, today.day, "PP", p.id)


def decode_payment_reference(hash_to_decode):
    return hashlib.sha1(hash_to_decode.decode("utf-8"))


def invoxia_position(invoxia_identifier: str):
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
            return invoxia_client.get_locations(device=tracker, max_count=1)[0]
    return None
