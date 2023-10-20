import unittest

from invoices.parsers.mt940 import MT940toOFXConverter


class TestMT940toOFXConverter(unittest.TestCase):

    def setUp(self):
        self.sample_mt940_data = """
:20:00103431-0001
:25:CCRALULL/LU860099780001034313
:28C:021/0001
:60F:C230606EUR000000007807,53
:61:2306060606DR000000000763,46N124PMT-ID0-20230524//FT2315786F6M
:86:124
?00PMT-ID0-20230524142033
?20VIREMENT VIA MULTILINE
?21VIREMENT COLLECTIF
?22PMT-ID0-20230524142033
?23FT2315786F6M                       
:62F:C230606EUR000000007044,07
"""
        
        self.sample_mt940_data2 = """
        :20:00103431-0001
:25:CCRALULL/LU860099780001034313
:28C:051/0001
:60F:C230816EUR000000127372,97
:61:2308150816CR000000000065,40N238NONREF//SP23228203170893
:86:238
?00BONIFICATION
?20BONIFICATION
?21REF: PP110869
?22SP23228203170893424243.09          
?30BGLLLULL
?32M. XXXX YYYY
?60M. XXXX YYYY
?613 IMPASSE EMILE DIDDERICH MONDORF-L
?62ES-BAINS-5616
?63LU
:61:2308160816DR000000002591,22N1242023081515415159//FT23228Q6K49
:86:124
?00202308151541515976MULTI
?20VIREMENT VIA MULTILINE
?2127/11039-66706
?22FT23228Q6K49                       
?30BILLLULLXXX
?31LU110022310167500800
?32MME MMMM PPPPP TTTT C
?33ABINET DE KINESITHERAPIE
?60MME MMMM PPPPP TTTT CABINET D
:61:2308160816DR000000011544,44N1242023081612434848//FT23228L9HYD
:86:124
?00202308161243484875MULTI
?20VIREMENT VIA MULTILINE
?21sous traitance Mai 2023
?22FT23228L9HYD                       
?30BBRUBEBBXXX
?31BE96363219856705
?32Ccccc Nnnnnnn
?60Ccccc Nnnnnnn
:62F:C230816EUR000000113302,71
"""

    def test_convert(self):
        converter = MT940toOFXConverter(self.sample_mt940_data)
        result = converter.convert()
        # Basic checks to ensure conversion happened
        self.assertIn('<OFX>', result)
        self.assertIn('<STMTTRN>', result)
        self.assertIn('<TRNTYPE>', result)
        self.assertIn('<DTPOSTED>', result)
        self.assertIn('<TRNAMT>', result)
        self.assertIn('<FITID>', result)
        self.assertIn('<MEMO>', result)
        self.assertIn('<MEMO>VIREMENT COLLECTIF</MEMO>', result)

    def test_convert2(self):
        converter = MT940toOFXConverter(self.sample_mt940_data2)
        result = converter.convert()
        # Basic checks to ensure conversion happened
        self.assertIn('<OFX>', result)
        self.assertIn('<STMTTRN>', result)
        self.assertIn('<TRNTYPE>', result)
        self.assertIn('<DTPOSTED>', result)
        self.assertIn('<TRNAMT>', result)
        self.assertIn('<FITID>', result)
        self.assertIn('<MEMO>', result)
        self.assertIn('<NAME>MME MMMM PPPPP TTTT C</NAME>', result)
        self.assertIn('<NAME>Ccccc Nnnnnnn</NAME>', result)
        self.assertIn('<MEMO>sous traitance Mai 2023</MEMO>', result)

    # Add more tests as needed

if __name__ == '__main__':
    unittest.main()
