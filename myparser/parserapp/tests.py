from django.urls import reverse
from django.test import TestCase
import json
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status
from .services.hh_parser import HHParser, HHTimeoutError, HHRequestError
from .serializers import vacancy_from_hh


class VacancySearchViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('vacancy_search')

    def test_search_with_query_params(self):
        """Тест поиска через query параметры"""
        mock_vacancies = [
            {
                'title': 'Python Developer',
                'company_name': 'Test Company',
                'description': 'Test description',
                'salary_from': 100000,
                'salary_to': 200000,
                'currency': 'RUB',
                'work_mode': 'remote',
                'location': 'Москва',
                'url': 'https://hh.ru/vacancy/123',
                'external_id': '123',
                'source': 'HH.ru'
            }
        ]
        
        with patch.object(HHParser, 'get_vacancies', return_value=mock_vacancies):
            response = self.client.get(
                self.url,
                {'search_phrase': 'python', 'page': 0, 'per_page': 20}
            )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertIn('vacancies', data)
        self.assertEqual(len(data['vacancies']), 1)
        self.assertEqual(data['vacancies'][0]['title'], 'Python Developer')

    def test_search_without_search_phrase(self):
        """Тест без обязательного параметра search_phrase"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_search_with_invalid_page(self):
        """Тест с невалидным параметром page"""
        response = self.client.get(
            self.url,
            {'search_phrase': 'python', 'page': 'invalid'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_search_with_negative_page(self):
        """Тест с отрицательным page"""
        response = self.client.get(
            self.url,
            {'search_phrase': 'python', 'page': -1}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_with_invalid_per_page(self):
        """Тест с невалидным per_page"""
        response = self.client.get(
            self.url,
            {'search_phrase': 'python', 'per_page': 'invalid'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_with_per_page_too_large(self):
        """Тест с per_page больше 100"""
        response = self.client.get(
            self.url,
            {'search_phrase': 'python', 'per_page': 101}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_with_per_page_zero(self):
        """Тест с per_page равным 0"""
        response = self.client.get(
            self.url,
            {'search_phrase': 'python', 'per_page': 0}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_with_hh_timeout(self):
        """Тест обработки таймаута HH API"""
        with patch.object(HHParser, 'get_vacancies', side_effect=HHTimeoutError('Timeout')):
            response = self.client.get(
                self.url,
                {'search_phrase': 'python'}
            )
        self.assertEqual(response.status_code, status.HTTP_504_GATEWAY_TIMEOUT)
        data = json.loads(response.content)
        self.assertIn('error', data)

    def test_search_with_hh_request_error(self):
        """Тест обработки ошибки запроса к HH API"""
        with patch.object(HHParser, 'get_vacancies', side_effect=HHRequestError('Error', status_code=500)):
            response = self.client.get(
                self.url,
                {'search_phrase': 'python'}
            )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = json.loads(response.content)
        self.assertIn('error', data)


class VacancySerializerTest(TestCase):
    def test_vacancy_from_hh_with_full_data(self):
        """Тест сериализации вакансии с полными данными"""
        hh_item = {
            'id': '123456',
            'name': 'Python Developer',
            'employer': {'name': 'Test Company'},
            'snippet': {'responsibility': 'Разработка на Python'},
            'salary': {
                'from': 100000,
                'to': 200000,
                'currency': 'RUB'
            },
            'schedule': {'id': 'remote'},
            'area': {'name': 'Москва'},
            'alternate_url': 'https://hh.ru/vacancy/123456'
        }
        
        result = vacancy_from_hh(hh_item)
        
        self.assertEqual(result['title'], 'Python Developer')
        self.assertEqual(result['company_name'], 'Test Company')
        self.assertEqual(result['description'], 'Разработка на Python')
        self.assertEqual(result['salary_from'], 100000)
        self.assertEqual(result['salary_to'], 200000)
        self.assertEqual(result['currency'], 'RUB')
        self.assertEqual(result['work_mode'], 'remote')
        self.assertEqual(result['location'], 'Москва')
        self.assertEqual(result['external_id'], '123456')
        self.assertEqual(result['source'], 'HH.ru')

    def test_vacancy_from_hh_with_missing_fields(self):
        """Тест сериализации вакансии с отсутствующими полями"""
        hh_item = {
            'id': '123',
            'name': 'Developer',
            'employer': {},
            'snippet': {},
            'salary': None,
            'schedule': {},
            'area': {},
            'alternate_url': ''
        }
        
        result = vacancy_from_hh(hh_item)
        
        self.assertEqual(result['title'], 'Developer')
        self.assertEqual(result['company_name'], '')
        self.assertEqual(result['description'], '')
        self.assertIsNone(result['salary_from'])
        self.assertIsNone(result['salary_to'])
        self.assertIsNone(result['currency'])
        self.assertIsNone(result['work_mode'])
        self.assertEqual(result['location'], '')
        self.assertEqual(result['external_id'], '123')

    def test_vacancy_work_mode_office(self):
        """Тест определения режима работы 'office'"""
        hh_item = {
            'id': '123',
            'name': 'Developer',
            'employer': {},
            'snippet': {},
            'salary': None,
            'schedule': {'id': 'fullDay'},
            'area': {},
            'alternate_url': ''
        }
        
        result = vacancy_from_hh(hh_item)
        self.assertEqual(result['work_mode'], 'office')

    def test_vacancy_work_mode_remote(self):
        """Тест определения режима работы 'remote'"""
        hh_item = {
            'id': '123',
            'name': 'Developer',
            'employer': {},
            'snippet': {},
            'salary': None,
            'schedule': {'id': 'remote'},
            'area': {},
            'alternate_url': ''
        }
        
        result = vacancy_from_hh(hh_item)
        self.assertEqual(result['work_mode'], 'remote')
