import csv
import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime

from ofxtools.header import make_header
from ofxtools.models import STMTTRN, OFX, BANKMSGSRSV1, BANKACCTFROM, STMTTRNRS, STMTRS, SIGNONMSGSRSV1, SONRS, STATUS, \
    BANKTRANLIST, LEDGERBAL
from ofxtools.utils import UTC


class CSVToOFXConverter:
    def __init__(self, csv_file, is_zip=False):
        self.is_zip = is_zip
        if is_zip:
            self.file_path = csv_file
            self.data = self._extract_zip_contents()
        else:
            self.data = self.parse_csv(csv_file)
        self.parsed_data = {}

    def _extract_zip_contents(self):
        # Extract and concatenate all MT940 files from the ZIP
        combined_data = ""
        zip_content = io.BytesIO(self.file_path)
        with zipfile.ZipFile(zip_content, 'r') as zip_ref:
            for file_name in zip_ref.namelist():
                with zip_ref.open(file_name) as file:
                    combined_data += file.read().decode('utf-8') + "\n"
        return combined_data

    def parse_csv(self, csv_content):
        data = []
        reader = csv.DictReader(io.StringIO(csv_content, newline='\n') , delimiter=';')

        for row in reader:
            # Optional: Strip whitespace from keys
            row = {k.strip(): v for k, v in row.items()}
            data.append(row)
        return data


    def convert(self):
        # Replace these with your bank's details
        bank_id = 'BANK_ID'
        account_id = 'ACCOUNT_ID'
        account_type = 'CHECKING'  # or 'SAVINGS', etc.
        bankacctfrom = BANKACCTFROM(bankid=bank_id, acctid=account_id, accttype=account_type)

        # Initialize transaction list
        transactions = []
        for row in self.data:
            # Parse the date and make it timezone-aware
            dt = datetime.strptime(row['Date transaction'], '%d/%m/%Y').replace(tzinfo=UTC)
            amount = float(row['Montant en EUR'].replace(',', '.'))
            memo = None
            if row['Communication 1']:
                memo = row['Communication 1'] + ' ' + row['Communication 2'] + ' ' + row['Communication 3'] + ' ' + row['Communication 4']
                # remove all whitespace at end of string
                memo = memo.rstrip()
                # max string is 32 chars
                memo = memo[:32]
            elif row['Nom de la contrepartie']:
                memo = row['Nom de la contrepartie']
                # remove all whitespace at end of string
                memo = memo.rstrip()
                # max string is 32 chars
                memo = memo[:32]

            # Create a transaction
            transaction = STMTTRN(trntype="DEBIT" if amount < 0 else "CREDIT",
                                  dtposted=dt,
                                  trnamt=amount,
                                  fitid=str(dt.timestamp()),
                                  memo=memo,
                                  name=row['Description'])
            transactions.append(transaction)
        # dtstart is the date of the first transaction
        dtstart = datetime.strptime(self.data[0]['Date transaction'], '%d/%m/%Y').replace(tzinfo=UTC)
        dtend = datetime.strptime(self.data[-1]['Date transaction'], '%d/%m/%Y').replace(tzinfo=UTC)

        # Add transactions to OFX structure
        banktranlist = BANKTRANLIST(*transactions, dtstart=dtstart, dtend=dtend)

        # Set up account information
        stmtrs = STMTRS(
            curdef="EUR",
            bankacctfrom=bankacctfrom,
            banktranlist=banktranlist,
            ledgerbal=LEDGERBAL(balamt=0, dtasof=datetime.now(tz=UTC))  # Adjust the ledger balance as needed
        )

        stmttrnrs = STMTTRNRS(trnuid='5678',
                              status=STATUS(code=0, severity='INFO', message="Transaction completed successfully"),
                              stmtrs=stmtrs)

        # Initialize OFX structure with signon message and bank transaction response
        sonrs = SONRS(status=STATUS(code=0, severity='INFO'), dtserver=datetime(2015, 1, 2, 17, tzinfo=UTC),
                      language='FRA')

        ofx = OFX(signonmsgsrsv1=SIGNONMSGSRSV1(sonrs=sonrs), bankmsgsrsv1=BANKMSGSRSV1(stmttrnrs), )
        root = ofx.to_etree()
        message = ET.tostring(root).decode()
        header = str(make_header(version=220))
        response = header + message

        return response

