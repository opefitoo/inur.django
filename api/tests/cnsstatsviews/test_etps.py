from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from api.serializers import EmployeeContractDetailSerializer
from api.tests.cnsstatsviews.base import AnotherBaseAuth
from invoices.employee import EmployeeContractDetail, Employee, JobPosition


class EmployeeContractDetailTestCase(AnotherBaseAuth, APITestCase):

    def setUp(self):
        self.testuser_aidesoignant = User.objects.create_user('testuser_aidesoignant', email='testuser@test.com', password='testing')
        job_position = JobPosition.objects.create(name='name 0')
        job_position.save()
        employee1 = Employee.objects.create(start_contract='2018-01-01',
                                            user=self.testuser_aidesoignant,
                                            occupation=job_position)
        employee1.save()
        super(EmployeeContractDetailTestCase, self).setUp()
        self.model_name = 'employeecontractdetail'
        self.model = EmployeeContractDetail
        self.serializer = EmployeeContractDetailSerializer
        # EmployeeContractDetail fields are  fields = ('start_date', 'number_of_hours', 'number_of_days_holidays', 'monthly_wage', 'contract_date',
        #                   'contract_signed_date', 'employee_trial_period_text', 'employee_special_conditions_text', 'index',
        #                   'career_rank', 'anniversary_career_rank', 'weekly_work_organization')
        self.items = [self.model.objects.create(start_date='2018-01-01',
                                                number_of_hours=30,
                                                number_of_days_holidays=32,
                                                monthly_wage=1000,
                                                contract_date='2018-01-01',
                                                contract_signed_date='2018-01-01',
                                                employee_trial_period_text='6 months',
                                                employee_special_conditions_text='None',
                                                index=200,
                                                career_rank='C3/126',
                                                anniversary_career_rank='2019-01-01',
                                                weekly_work_organization='6 hours',
                                                employee_link=employee1),]



        self.valid_payload = {
            'start_date': '2018-01-01',
            'number_of_hours': 30,
            'number_of_days_holidays': 32,
            'monthly_wage': 1000,
            'contract_date': '2018-01-01',
            'contract_signed_date': '2018-01-01',
            'employee_trial_period_text': '6 months',
            'employee_special_conditions_text': 'None',
            'index': 200,
            'career_rank': 'C3/126',
            'anniversary_career_rank': '2019-01-01',
            'weekly_work_organization': '6 hours',
            'employee_link': employee1
        }
        self.invalid_payload = {
            'start_date': '2018-01-01',
            'number_of_hours': 30,
            'number_of_days_holidays': 32,
            'monthly_wage': 1000,
            'contract_date': '2018-01-01',
            'contract_signed_date': '2018-01-01',
            'employee_trial_period_text': '6 months',
            'employee_special_conditions_text': 'None',
            'index': 200,
            'career_rank': 'C3/126',
            'anniversary_career_rank': '2019-01-01',
            'weekly_work_organization': '6 hours',
            'employee_link': employee1
        }

    def test_get_all(self):
        care_codes = self.model.objects.all()
        serializer = self.serializer(care_codes, many=True)

        self._require_login()
        url = reverse('api:' + self.model_name + '-list')
        response = self.client.get(url)

        self.assertEqual(response.data['count'], len(serializer.data))
        self.assertEqual(response.status_code, status.HTTP_200_OK)



    def test_get_valid_single(self):
        employee_contract_detail = self.model.objects.get(pk=self.items[0].id)

        # Serialize the EmployeeContractDetail object using EmployeeContractDetailSerializer
        serializer = EmployeeContractDetailSerializer(employee_contract_detail)

        self._require_login()
        url = reverse('api:' + self.model_name + '-detail', kwargs={'pk': self.items[0].id})
        response = self.client.get(url)

        expected_data = serializer.data
        actual_data = response.data
        expected_data.pop('employee_link', None)
        actual_data.pop('employee_link', None)
        self.assertEqual(expected_data, actual_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_how_many_employees_with_specific_cct_sas_grade(self):
        # Create an instance of the APIClient
        self._require_login()
        # Define the URL for the view
        url = reverse('api:how-many-employees-with-specific-cct-sas-grade')  # Replace with the actual URL name

        # Define the POST data with the desired career_rank
        data = {'career_rank': 'C3/126'}  # Replace with the desired career_rank

        # Make a POST request to the view
        response = self.client.post(url, data, format='json')

        # Assert that the response status code is HTTP 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the response data (assuming you know the expected employee count)
        expected_employee_count = 1  # Replace with the expected count
        self.assertEqual(response.data, expected_employee_count)


