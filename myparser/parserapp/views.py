from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.http import JsonResponse
from django.db.models import Q
from .models import Vacancy
from .serializers import VacancySearchSerializer, VacancySerializer, VacancyModelSerializer
from .services.hh_parser import HHParser, HHTimeoutError, HHRequestError
from .services.vacancy_service import VacancyService


def api_info(request):
    """Информация об API endpoints"""
    return JsonResponse({
        'message': 'Vacancy Parser API',
        'endpoints': {
            'search': {
                'url': '/api/search/',
                'method': 'GET',
                'description': 'Поиск вакансий на HeadHunter',
                'parameters': {
                    'search_phrase': 'Поисковая фраза (обязательно)',
                    'page': 'Номер страницы (по умолчанию 0)',
                    'per_page': 'Количество вакансий на странице (по умолчанию 20)',
                    'save': 'Сохранить результаты в БД (true/false)',
                    'update': 'Обновить существующие вакансии (true/false, работает с save=true)'
                },
                'example': '/api/search/?search_phrase=python&per_page=10&save=true'
            },
            'vacancies': {
                'url': '/api/vacancies/',
                'method': 'GET',
                'description': 'Получить сохраненные вакансии из базы данных',
                'parameters': {
                    'search': 'Поиск по названию и описанию',
                    'location': 'Фильтр по городу',
                    'work_mode': 'Фильтр по режиму работы (office/remote/hybrid)',
                    'company': 'Фильтр по названию компании',
                    'salary_min': 'Минимальная зарплата',
                    'page': 'Номер страницы',
                    'per_page': 'Количество на странице (по умолчанию 20)'
                },
                'example': '/api/vacancies/?search=python&location=Москва&work_mode=remote'
            }
        },
        'admin': '/admin/'
    })


class VacancySearchView(APIView):
    """
    API endpoint для поиска вакансий на HeadHunter.
    
    GET /api/search/?search_phrase=python&page=0&per_page=20
    """
    def get(self, request):
         # Валидация входных параметров через сериализатор
        serializer = VacancySearchSerializer(data=request.query_params)

        if not serializer.is_valid():
            return Response(
                {'error': 'Validation error', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        search_phrase = validated_data['search_phrase']
        page = validated_data.get('page', 0)
        per_page = validated_data.get('per_page', 20)
        
        # Проверяем, нужно ли сохранять в БД
        save_to_db = request.query_params.get('save', 'false').lower() == 'true'
        update_existing = request.query_params.get('update', 'false').lower() == 'true'

        # Выполняем запрос к HH API
        try:
            parser = HHParser()
            vacancies = parser.get_vacancies(
                search_phrase,
                page=page,
                per_page=per_page
            )

            # Сохраняем в БД, если указано
            save_stats = None
            if save_to_db:
                try:
                    service = VacancyService()
                    save_stats = service.save_vacancies(vacancies, update_existing=update_existing)
                except Exception as e:
                    # Логируем ошибку, но не прерываем выполнение запроса
                    return Response({
                        'error': 'Error saving vacancies to database',
                        'details': str(e),
                        'vacancies': VacancySerializer(vacancies, many=True).data,
                        'count': len(vacancies),
                        'page': page,
                        'per_page': per_page
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Сериализуем результат
            vacancy_serializer = VacancySerializer(vacancies, many=True)

            response_data = {
                'vacancies': vacancy_serializer.data,
                'count': len(vacancies),
                'page': page,
                'per_page': per_page
            }
            
            # Добавляем статистику сохранения, если было сохранение
            if save_stats:
                response_data['save_stats'] = save_stats

            return Response(response_data)

                
        except HHTimeoutError as e:
            return Response(
                {
                    'error': 'Request to HeadHunter API timed out',
                    'details': str(e)
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except HHRequestError as e:
            status_code = e.status_code if e.status_code else status.HTTP_502_BAD_GATEWAY
            return Response(
                {
                    'error': 'Error communicating with HeadHunter API',
                    'details': str(e)
                },
                status=status_code  
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Internal server error',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VacancyListView(APIView):
    """
    API endpoint для получения сохраненных вакансий из базы данных.
    
    GET /api/vacancies/?search=python&location=Москва&work_mode=remote&page=1
    """
    pagination_class = PageNumberPagination
    
    def get(self, request):
        try:
            # Получаем параметры фильтрации
            search_query = request.query_params.get('search', '').strip()
            location = request.query_params.get('location', '').strip()
            work_mode = request.query_params.get('work_mode', '').strip()
            company_name = request.query_params.get('company', '').strip()
            salary_min = request.query_params.get('salary_min', '').strip()
            
            # Начинаем с базового QuerySet
            queryset = Vacancy.objects.all()
            
            # Применяем фильтры
            if search_query:
                queryset = queryset.filter(
                    Q(title__icontains=search_query) | 
                    Q(description__icontains=search_query)
                )
            
            if location:
                queryset = queryset.filter(location__icontains=location)
            
            if work_mode:
                queryset = queryset.filter(work_mode=work_mode)
            
            if company_name:
                queryset = queryset.filter(company_name__icontains=company_name)
            
            if salary_min:
                try:
                    salary_min_value = float(salary_min)
                    queryset = queryset.filter(
                        Q(salary_from__gte=salary_min_value) | 
                        Q(salary_to__gte=salary_min_value)
                    )
                except ValueError:
                    pass
            
            # Применяем пагинацию
            paginator = PageNumberPagination()
            paginator.page_size = int(request.query_params.get('per_page', 20))
            page = paginator.paginate_queryset(queryset, request)
            
            if page is not None:
                serializer = VacancyModelSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            
            # Если пагинация не применена
            serializer = VacancyModelSerializer(queryset, many=True)
            return Response({
                'vacancies': serializer.data,
                'count': queryset.count()
            })
            
        except Exception as e:
            return Response(
                {
                    'error': 'Internal server error',
                    'details': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
