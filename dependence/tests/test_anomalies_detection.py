import unittest
from unittest.mock import patch, MagicMock

from django.test import TestCase

from dependence.invoicing import detect_anomalies, LongTermCareMonthlyStatementSending


# from invoices import settings as my_settings
# settings.configure(default_settings=my_settings)
# django.setup()


class TestDetectAnomalies(TestCase):
    @patch('dependence.invoicing.ET.parse')
    @patch('dependence.invoicing.LongTermCareInvoiceFile.objects.filter')
    def test_detect_anomalies(self, mock_filter, mock_parse):
        # Mock the XML file parsing
        mock_tree = MagicMock()
        mock_parse.return_value = mock_tree

        # Mock the XML root element
        mock_root = MagicMock()
        mock_tree.getroot.return_value = mock_root

        # Mock the XML elements
        mock_montant_net_element = MagicMock()
        mock_montant_brut_element = MagicMock()
        mock_root.find.side_effect = [mock_montant_net_element, mock_montant_brut_element]

        # Mock the text content of the XML elements
        mock_montant_net_element.text = '100'
        mock_montant_brut_element.text = '100'

        # Mock the instance
        instance = LongTermCareMonthlyStatementSending()

        # Call the function
        result = detect_anomalies(instance)

        # Assert that the function returns None (no anomalies detected)
        self.assertIsNone(result)

        # Assert that the correct methods were called
        mock_parse.assert_called_once()
        mock_tree.getroot.assert_called_once()
        mock_root.find.assert_any_call('./entete/paiementGroupeTraitement/montantNet')
        mock_root.find.assert_any_call('./entete/paiementGroupeTraitement/montantBrut')


if __name__ == '__main__':
    unittest.main()
