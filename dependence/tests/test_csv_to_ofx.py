import unittest

from invoices.parsers.csv2ofx import CSVToOFXConverter


class TestCSVtoOFXConverter(unittest.TestCase):

    def setUp(self):
        self.sample_csv_data = """Date transaction;Description;Date valeur;Montant en EUR;Extrait;Solde journalier;Opération;Communication 1;Communication 2;Communication 3;Communication 4;Compte bénéficiaire;Nom de la contrepartie;Adresse de la contrepartie;Localité de la contrepartie
01/02/2023;IBAN LU19 0000 1313 0000 XXXX;01/02/2023;-781,37;2;110285,14;OPA;;;;;;IBAN LU19 0011 1363 7071 7660;;
01/02/2023;TPV 2300 CACTUS HOWALD 30.01;01/02/2023;-211,87;2;110073,27;DEB;;;;;;TPV 2300 CACTUS HOWALD 30.01;;
01/02/2023;Cyyyy xxxx Marie;01/02/2023;-69,59;2;110003,68;VIR;ndf Janvier 2023;;;;LU970099780000351817;CECE Christiane Marie;;
02/02/2023;TPV LA RUSTICANA II31.01;02/02/2023;-122,8;2;109880,88;DEB;;;;;;TPV LA RUSTICANA II31.01;;
02/02/2023;TPV 3800 CACTUS BONNEVOIE 31.01;02/02/2023;-21,85;2;109859,03;DEB;;;;;;TPV 3800 CACTUS BONNEVOIE 31.01;;
06/02/2023;DOMICILIATION ARAL LUXEMBOURG S.A. /MISTRAL- SO//ZZ1DG8B8IXCCY6NBW///INV/0001215610/SEPA 31.1.20;06/02/2023;-669,47;2;105355,46;SDD;/MISTRAL-SO//ZZ1DG8B8IXCCY6NBW///IN;V/0001215610/SEPA 31.1.2023/0050684;594;;LU150030546657960000;ARAL LUXEMBOURG S.A.;;
"""

    def test_convert(self):
        converter = CSVToOFXConverter(self.sample_csv_data)
        result = converter.convert()
        # Basic checks to ensure conversion happened
        self.assertIn('<OFX>', result)
        self.assertIn('<STMTTRN>', result)
        self.assertIn('<TRNTYPE>', result)
        self.assertIn('<DTPOSTED>', result)
        self.assertIn('<TRNAMT>', result)
        self.assertIn('<FITID>', result)
        self.assertIn('<MEMO>', result)
        self.assertIn('<NAME>TPV 2300 CACTUS HOWALD 30.01</NAME>', result)

    def test_convert2(self):
        converter = CSVToOFXConverter(self.sample_csv_data)
        result = converter.convert()
        # Basic checks to ensure conversion happened
        self.assertIn('<OFX>', result)
        self.assertIn('<STMTTRN>', result)
        self.assertIn('<TRNTYPE>', result)
        self.assertIn('<DTPOSTED>', result)
        self.assertIn('<TRNAMT>', result)
        self.assertIn('<FITID>', result)
        self.assertIn('<MEMO>', result)
        self.assertIn('<NAME>TPV 2300 CACTUS HOWALD 30.01</NAME>', result)
        self.assertIn('<NAME>IBAN LU19 0000 1313 0000 XXXX</NAME>', result)
        self.assertIn('<MEMO>/MISTRAL-SO//ZZ1DG8B8IXCCY6NBW//</MEMO>', result)
        self.assertIn('<NAME>Cyyyy xxxx Marie</NAME>', result)

    # Add more tests as needed

if __name__ == '__main__':
    unittest.main()
