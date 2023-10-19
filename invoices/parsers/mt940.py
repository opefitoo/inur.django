import re
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal

from ofxtools.header import make_header
from ofxtools.models import OFX, SIGNONMSGSRSV1, SONRS, STATUS, BANKMSGSRSV1, STMTTRNRS
from ofxtools.models.bank import STMTRS, BANKACCTFROM, LEDGERBAL, BANKTRANLIST
from ofxtools.models.bank.stmt import STMTTRN
from ofxtools.utils import UTC


class MT940toOFXConverter:
    # def __init__(self, filename):
    #     with open(filename, 'r') as mt940_file:
    #         self.data = mt940_file.read()
    #     self.parsed_data = {}

    def __init__(self, file_content: str):
        self.data = file_content
        self.parsed_data = {}

    def convert(self):
        mt940_data = self.data

        # Split the data into lines
        lines = mt940_data.split('\n')

        # Initialize variables
        transactions = []
        current_transaction = {}
        is_transaction = False
        closing_balance = None
        closing_date = None

        # Iterate through the lines
        for line in lines:
            if line.startswith(':61:'):
                is_transaction = True
                current_transaction['61'] = line[4:]
            elif line.startswith(':86:') and is_transaction:
                current_transaction['86'] = line[4:]
            elif line.startswith('?21') and is_transaction:
                current_transaction['payment_reference'] = line[4:].strip()
            elif line.startswith('?32') and is_transaction:
                current_transaction['payee'] = line[4:].strip()
            elif line.startswith(':62F:'):
                cleaned_string = line.replace('\n', '').replace('\r', '')
                match = re.search(r'^:62F:[CD](?P<date>\d{6})[A-Z]{3}(?P<amount>[\d,]+,\d{2})$', cleaned_string)
                if match:
                    closing_date = datetime.strptime(match.group('date'), '%y%m%d').strftime('%Y%m%d000000')
                    closing_balance = match.group('amount').replace(',', '.')
                if is_transaction:
                    transactions.append(current_transaction)
                    current_transaction = {}
                    is_transaction = False

        # Convert MT940 transactions to OFX format
        ofx_transactions = []
        for transaction in transactions:
            match = re.search(
                r'^(?P<value_date>\d{6})(?P<entry_date>\d{4})?(?P<operation_type>[CD]R)(?P<amount>\d+,\d{2}).*//(?P<transaction_id>.+)$',
                transaction['61'])

            value_date = match.group('value_date')
            value_date_utc = datetime.strptime(value_date, '%y%m%d').replace(tzinfo=UTC)
            operation_type = match.group('operation_type')
            amount = match.group('amount').replace(',', '.')
            amount_in_decimal = Decimal(amount)
            transaction_id = match.group('transaction_id')

            # Convert operation type from MT940 to OFX format
            if operation_type == 'CR':
                trntype = "CREDIT"
            else:
                amount_in_decimal = -amount_in_decimal
                trntype = "DEBIT"

            stmttrn = STMTTRN(
                trntype=trntype,
                dtposted=value_date_utc,
                trnamt=amount_in_decimal,
                fitid=transaction_id,
                memo=transaction.get('payment_reference', ''),
                name=transaction.get('payee', '')
            )
            ofx_transactions.append(stmttrn)

        bankfrom = BANKACCTFROM(bankid='111000025', acctid='123456789012', accttype='CHECKING')
        banktranlist = BANKTRANLIST(*ofx_transactions, dtstart=value_date_utc, dtend=value_date_utc)
        stmtrs = STMTRS(
            curdef='EUR',
            bankacctfrom=bankfrom,
            banktranlist=banktranlist,
            ledgerbal=LEDGERBAL(balamt=Decimal(closing_balance), dtasof=closing_date)
        )

        stmttrnrs = STMTTRNRS(trnuid='5678',
                              status=STATUS(code=0, severity='INFO', message="Transaction completed successfully"),
                              stmtrs=stmtrs)

        sonrs = SONRS(status=STATUS(code=0, severity='INFO'), dtserver=datetime(2015, 1, 2, 17, tzinfo=UTC),
                      language='FRA')

        ofx = OFX(signonmsgsrsv1=SIGNONMSGSRSV1(sonrs=sonrs), bankmsgsrsv1=BANKMSGSRSV1(stmttrnrs), )

        root = ofx.to_etree()
        message = ET.tostring(root).decode()
        header = str(make_header(version=220))
        response = header + message

        return response




