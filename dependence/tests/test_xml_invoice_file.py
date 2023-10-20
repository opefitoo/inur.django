import os
import unittest
import xml.etree.ElementTree as ET


class XMLParsingTestCase(unittest.TestCase):

    def test_parse_xml(self):
        # Load XML data from file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, 'fixtures', 'test_data', 'test1.xml')
        tree = ET.parse(file_path)
        with open(file_path, 'r', encoding='utf-8') as file:
            xml_data = file.read()

        # Parse XML data
        root = ET.fromstring(xml_data)

        grand_total_montantBrut = 0
        grand_total_montantNet = 0


        for facture in root.findall('.//facture'):

            total_montantBrut = 0
            total_montantNet = 0

            # Loop through each 'prestation' under 'facture'
            for prestation in facture.findall('.//prestation'):
                montantBrut = float(prestation.find('.//demandePrestation/montantBrut').text)
                montantNet = float(prestation.find('.//demandePrestation/montantNet').text)


                total_montantBrut += montantBrut
                total_montantNet += montantNet

            # Assert and output the totals
            total_montantBrut_rounded = round(total_montantBrut, 2)
            total_montantNet_rounded = round(total_montantNet, 2)
            self.assertEqual(total_montantBrut_rounded, float(facture.find('.//demandeFacture/montantBrut').text))
            self.assertEqual(total_montantNet_rounded, float(facture.find('.//demandeFacture/montantNet').text))

            print(f"Total montantBrut for facture {facture.find('.//referenceFacture').text}: {total_montantBrut}")
            print(f"Total montantNet for facture {facture.find('.//referenceFacture').text}: {total_montantNet}")

            grand_total_montantBrut += total_montantBrut_rounded
            grand_total_montantNet += total_montantNet_rounded

        self.assertEqual(round(grand_total_montantBrut, 2), float(root.find('.//demandeDecompte/montantBrut').text))
        self.assertEqual(round(grand_total_montantNet, 2), float(root.find('.//demandeDecompte/montantNet').text))

    def test_parse_xml_2(self):
        # Load XML data from file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, 'fixtures', 'test_data', 'test2.xml')
        tree = ET.parse(file_path)
        with open(file_path, 'r', encoding='utf-8') as file:
            xml_data = file.read()

        # Parse XML data
        root = ET.fromstring(xml_data)

        grand_total_montantBrut = 0
        grand_total_montantNet = 0


        for facture in root.findall('.//facture'):

            total_montantBrut = 0
            total_montantNet = 0

            # Loop through each 'prestation' under 'facture'
            for prestation in facture.findall('.//prestation'):
                montantBrut = float(prestation.find('.//demandePrestation/montantBrut').text)
                montantNet = float(prestation.find('.//demandePrestation/montantNet').text)

                print(f"montantBrut for facture {facture.find('.//referenceFacture').text}: {montantBrut}")
                print(f"montantNet for facture {facture.find('.//referenceFacture').text}: {montantNet}")

                total_montantBrut += montantBrut
                total_montantNet += montantNet

            # Assert and output the totals
            total_montantBrut_rounded = round(total_montantBrut, 2)
            total_montantNet_rounded = round(total_montantNet, 2)
            self.assertEqual(total_montantBrut_rounded, float(facture.find('.//demandeFacture/montantBrut').text))
            self.assertEqual(total_montantNet_rounded, float(facture.find('.//demandeFacture/montantNet').text))


            grand_total_montantBrut += total_montantBrut_rounded
            grand_total_montantNet += total_montantNet_rounded

        self.assertEqual(round(grand_total_montantBrut, 2), float(root.find('.//demandeDecompte/montantBrut').text))
        self.assertEqual(round(grand_total_montantNet, 2), float(root.find('.//demandeDecompte/montantNet').text))
        print(f"Grand total montantBrut: {grand_total_montantBrut}")
        print(f"Grand total montantNet: {grand_total_montantNet}")


