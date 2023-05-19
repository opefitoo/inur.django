from _decimal import Decimal
from datetime import date

from django.test import TestCase

from dependence.longtermcareitem import LongTermPackage, LongTermPackagePrice


class LongTermPackagePriceTest(TestCase):

    def test_price_per_year_month(self):
        LongTermPackage.objects.filter(code="TESTCODE").delete()
        package, created = LongTermPackage.objects.get_or_create(dependence_level=1, package=True, code="TESTCODE", description="TESTDESC")
        self.create = LongTermPackagePrice.objects.get_or_create(package=LongTermPackage.objects.get(code="TESTCODE"),
                                                                 start_date=date(2023, 4, 1), price=10.00)
        LongTermPackagePrice.objects.get_or_create(package=LongTermPackage.objects.get(code="TESTCODE"),
                                            start_date=date(2023, 3, 1),
                                            end_date=date(2023,3,31),
                                            price=5.00)
        self.assertEqual(package.price_per_year_month(year=2023, month=3), Decimal('5.00'))
        self.assertEqual(package.price_per_year_month(2023,4), Decimal('10.00'))
        self.assertIsNone(package.price_per_year_month(2023,1))

