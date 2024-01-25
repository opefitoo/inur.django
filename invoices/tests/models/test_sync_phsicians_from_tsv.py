from io import StringIO

from django.core.files import File
from django.test import TestCase

from invoices.actions.physicians import sync_physicians_from_tsv
from invoices.models import Physician


class SyncPhysiciansFromTSVTest(TestCase):
    def setUp(self):
        # Create a sample TSV file
        self.tsv_data = StringIO("88001995ALBALBNO ANNA-CRICRINA EP.RIRIS         9, RUE HENRI TUDOR                      L -4489  BELVAUX                        SA 2017050430001231\n" +
                                 "22003110BAUBAUN LAULAU                          3, KRIIBSEBAACH                         L -9365  EPPELDORF                      SA 2017040930001231")
        self.tsv_file = File(self.tsv_data , name='physicians.tsv')

    def test_sync_physicians_from_tsv(self):
        # Call the function with the sample TSV file
        sync_physicians_from_tsv(self.tsv_file)

        # Check that a Physician was created
        self.assertEqual(Physician.objects.count(), 2)

        # Check that the Physician's details are correct
        physician = Physician.objects.get(provider_code="88001995")
        self.assertEqual(physician.provider_code, "88001995")
        self.assertEqual(physician.full_name_from_cns, "ALBALBNO ANNA-CRICRINA EP.RIRIS")
        # ... continue for the rest of the fields

    def test_update_of_existing_physician(self):
        # Create a Physician with the same provider_code
        physician = Physician.objects.create(
            provider_code="88001995",
            name="ALBALBNO",
            first_name="ANNA-CRICRINA",
            address="9, RUE HENRI TUDOR",
            zipcode="L -4489",
            city="BELVAUX",
            cns_speciality_code="SA",
            practice_start_date="2017-05-04",
            practice_end_date="2017-12-31",
        )

        # Call the function with the sample TSV file
        sync_physicians_from_tsv(self.tsv_file)

        # Check that the Physician was updated
        physician.refresh_from_db()
        self.assertEqual(physician.full_name_from_cns, "ALBALBNO ANNA-CRICRINA EP.RIRIS")
        # ... continue for the rest of the fields

    def tearDown(self):
        # Close the file after the test
        self.tsv_file.close()
