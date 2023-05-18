from _decimal import Decimal
from datetime import date

from django.test import TestCase

from dependence.invoicing import LongTermCareInvoiceLine, LongTermCareInvoiceFile, LongTermCareInvoiceItem
from dependence.longtermcareitem import LongTermPackage, LongTermPackagePrice
from invoices.models import Patient


class TestLongTermCareInvoiceItemAndLine(TestCase):
    def setUp(self):
        self.patient_john = Patient.objects.create(id=1309, name="John", is_under_dependence_insurance=True,
                                                   date_of_exit=None)
    def test_LongTermCareInvoiceLine_calculate_price(self):
        LongTermPackage.objects.create(dependence_level=1, package=True, code="TESTCODE", description="TESTDESC")
        LongTermPackagePrice.objects.create(package=LongTermPackage.objects.get(code="TESTCODE"),
                                            start_date=date(2023, 4, 1),
                                            price=10.00)
        line = LongTermCareInvoiceLine.objects.get_or_create(
            invoice=LongTermCareInvoiceFile.objects.create(patient=self.patient_john,
                                                           invoice_start_period=date(
                                                               2023, 4, 1),
                                                           invoice_end_period=date(
                                                               2023, 4, 30)),
            start_period=date(2023, 4, 1),
            end_period=date(2023, 4, 30),
            long_term_care_package=LongTermPackage.objects.get(code="TESTCODE"))
        self.assertEqual(line[0].calculate_price(), Decimal('300.00'))

    def test_LongTermCareInvoiceLine_calculate_price_2_days_period(self):
        LongTermPackage.objects.create(dependence_level=1, package=True, code="TESTCODE", description="TESTDESC")
        LongTermPackagePrice.objects.create(package=LongTermPackage.objects.get(code="TESTCODE"),
                                            start_date=date(2023, 4, 1),
                                            price=10.00)
        line = LongTermCareInvoiceLine.objects.get_or_create(
            invoice=LongTermCareInvoiceFile.objects.create(patient=self.patient_john,
                                                           invoice_start_period=date(
                                                               2023, 4, 1),
                                                           invoice_end_period=date(
                                                               2023, 4, 30)),
            start_period=date(2023, 4, 1),
            end_period=date(2023, 4, 2),
            long_term_care_package=LongTermPackage.objects.get(code="TESTCODE"))
        self.assertEqual(line[0].calculate_price(), Decimal('20.00'))

    def test_LongTermCareInvoiceItem(self):
        LongTermPackage.objects.create(dependence_level=1, package=False, code="TESTCODE", description="TESTDESC")
        LongTermPackagePrice.objects.create(package=LongTermPackage.objects.get(code="TESTCODE"),
                                            start_date=date(2023, 4, 1),
                                            price=10.00)
        item = LongTermCareInvoiceItem.objects.get_or_create(
            invoice=LongTermCareInvoiceFile.objects.create(patient=self.patient_john,
                                                           invoice_start_period=date(
                                                               2023, 4, 1),
                                                           invoice_end_period=date(
                                                               2023, 4, 30)),
            care_date=date(2023, 4, 1),
            long_term_care_package=LongTermPackage.objects.get(code="TESTCODE"))
        self.assertEqual(item[0].calculate_price(), Decimal('10.00'))
    def test_LongTermCareInvoiceItem_dates_differ(self):
        LongTermPackage.objects.create(dependence_level=1, package=False, code="TESTCODE", description="TESTDESC")
        LongTermPackagePrice.objects.create(package=LongTermPackage.objects.get(code="TESTCODE"),
                                            start_date=date(2023, 4, 1),
                                            price=10.00)
        LongTermPackagePrice.objects.create(package=LongTermPackage.objects.get(code="TESTCODE"),
                                            start_date=date(2023, 3, 1),
                                            end_date=date(2023, 3, 31),
                                            price=5.00)
        item_april = LongTermCareInvoiceItem.objects.get_or_create(
            invoice=LongTermCareInvoiceFile.objects.create(patient=self.patient_john,
                                                           invoice_start_period=date(
                                                               2023, 4, 1),
                                                           invoice_end_period=date(
                                                               2023, 4, 30)),
            care_date=date(2023, 4, 1),
            long_term_care_package=LongTermPackage.objects.get(code="TESTCODE"))
        item_march = LongTermCareInvoiceItem.objects.get_or_create(
            invoice=LongTermCareInvoiceFile.objects.create(patient=self.patient_john,
                                                           invoice_start_period=date(
                                                               2023, 3, 1),
                                                           invoice_end_period=date(
                                                               2023, 3, 31)),
            care_date=date(2023, 3, 15),
            long_term_care_package=LongTermPackage.objects.get(code="TESTCODE"))
        self.assertEqual(item_april[0].calculate_price(), Decimal('10.00'))
        self.assertEqual(item_march[0].calculate_price(), Decimal('5.00'))


