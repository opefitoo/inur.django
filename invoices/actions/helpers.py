import hashlib
from typing import List

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
