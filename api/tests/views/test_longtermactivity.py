from datetime import datetime

from constance.test import override_config
from django.contrib.auth.models import User
from django.utils.datetime_safe import date
from rest_framework.test import APITestCase

from api.serializers import LongTermMonthlyActivitySerializer
from api.tests.views.base import BaseTestCase
from dependence.activity import LongTermMonthlyActivity, LongTermMonthlyActivityDetail, LongTermMonthlyActivityFile
from dependence.longtermcareitem import LongTermCareItem
from invoices.models import Patient


class LongTermMonthlyActivityTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        LongTermCareItem.objects.create(code='AEVH03', short_description='AEVH03')
        LongTermCareItem.objects.create(code='AEVM15', short_description='AEVM15')
        LongTermCareItem.objects.create(code='AMD-GI', short_description='AMD-GI')
        # Delete any existing user with the same username
        User.objects.filter(username='testuser').delete()

        super(LongTermMonthlyActivityTestCase, self).setUp()
        self.model_name = 'longtermmonthlyactivity'
        self.model = LongTermMonthlyActivity
        self.serializer = LongTermMonthlyActivitySerializer

        date = datetime.now()
        patient_0 = Patient.objects.create(code_sn='code_sn0',
                                           first_name='first name 0',
                                           name='name 0',
                                           address='address 0',
                                           zipcode='zipcode 0',
                                           city='city 0',
                                           phone_number='000')
        patient_1 = Patient.objects.create(id=1515,
                                           code_sn='code_sn1',
                                           first_name='first name 1',
                                           name='name 1',
                                           address='address 1',
                                           zipcode='zipcode 1',
                                           city='city 1',
                                           phone_number='111')

        self.items = [self.model.objects.create(year=2023,
                                                month=5,
                                                patient=patient_0),
                      self.model.objects.create(year=2023,
                                                month=6,
                                                patient=patient_0),
                      self.model.objects.create(year=2023,
                                                month=5,
                                                patient=patient_1),
                      self.model.objects.create(year=2023,
                                                month=6,
                                                patient=patient_1)]

        self.valid_payload = {
            "year": 2023,
            "month": 1,
            "patient": 1515,
            "activity_details": [
                {
                    "activity": "AEVH03",
                    "quantity": 2,
                    "activity_date": "2023-01-03",

                },
                {
                    "activity": "AEVH03",
                    "quantity": 3,
                    "activity_date": "2023-01-04",
                }
            ]
        }

        self.invalid_payload = {
            'employee': '',
            'start_date': date.strftime('%Y-%m-%d')
        }

    def test_sample_from_google_sheet(self):
        patient_0 = Patient.objects.create(id=1313,
                                           code_sn='code_sn0',
                                           first_name='first name 0',
                                           name='name 0',
                                           address='address 0',
                                           zipcode='zipcode 0',
                                           city='city 0',
                                           phone_number='000')

        payload = {
            "activity_details": [
                {
                    "activity_date": "2023-03-01",
                    "activity": "AEVH03",
                    "quantity": 1
                },

                {
                    "activity_date": "2023-03-31",
                    "activity": "AEVM15",
                    "quantity": 1
                },
                {
                    "activity_date": "2023-03-31",
                    "activity": "AMD-GI",
                    "quantity": 3
                }
            ],
            "patient": 1313,
            "year": 2023,
            "month": 3
        }
        # use payload to create a new LongTermMonthlyActivity
        serializer = LongTermMonthlyActivitySerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # LongTermMonthlyActivity.objects.create(**serializer.validated_data)
        # check if the LongTermMonthlyActivity is created
        self.assertEqual(LongTermMonthlyActivity.objects.filter(year=2023, month=3).count(), 1)
        long_term_activity = LongTermMonthlyActivity.objects.filter(year=2023, month=3).get()
        # check if the LongTermMonthlyActivity has the right patient
        self.assertEqual(long_term_activity.patient, patient_0)
        self.assertEqual(
            LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=long_term_activity).count(), 3)

    @override_config(CODE_PRESTATAIRE='3778899')
    def test_xml_creation(self):
        patient_1313 = Patient.objects.create(id=1313,
                                              code_sn='1977010164522',
                                              first_name='first 1313',
                                              name='name 1313',
                                              address='address 0',
                                              zipcode='zipcode 0',
                                              city='city 0',
                                              phone_number='000')
        patient_1414 = Patient.objects.create(id=1414,
                                              code_sn='1980020230022',
                                              first_name='first 1414',
                                              name='name 1414',
                                              address='address',
                                              zipcode='zipcode',
                                              city='city 0',
                                              phone_number='000')

        payload = {
            "activity_details": [
                {
                    "activity_date": "2023-03-01",
                    "activity": "AEVH03",
                    "quantity": 1
                },

                {
                    "activity_date": "2023-03-31",
                    "activity": "AEVM15",
                    "quantity": 1
                },
                {
                    "activity_date": "2023-03-31",
                    "activity": "AMD-GI",
                    "quantity": 3
                }
            ],
            "patient": 1313,
            "year": 2023,
            "month": 3
        }

        serializer = LongTermMonthlyActivitySerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        payload = {
            "activity_details": [
                {
                    "activity_date": "2023-03-01",
                    "activity": "AEVH03",
                    "quantity": 1
                },

                {
                    "activity_date": "2023-03-02",
                    "activity": "AEVM15",
                    "quantity": 1
                },
                {
                    "activity_date": "2023-03-03",
                    "activity": "AMD-GI",
                    "quantity": 3
                }
            ],
            "patient": 1414,
            "year": 2023,
            "month": 3
        }
        serializer = LongTermMonthlyActivitySerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(LongTermMonthlyActivity.objects.filter(year=2023, month=3).count(), 2)
        file = LongTermMonthlyActivityFile.objects.create(
            year=2023,
            month=3,
            version_number=0,
            provider_date_of_sending=date.today())
        for ll in LongTermMonthlyActivity.objects.filter(year=2023, month=3).all():
            file.monthly_activities.add(ll)
        self.assertEqual(file.monthly_activities.count(), 2)
        print(file.generate_xml_using_xmlschema())
