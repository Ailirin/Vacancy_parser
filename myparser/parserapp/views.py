from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import VacancySearchSerializer, VacancySerializer
from .services.hh_parser import HHParser, HHTimeoutError, HHRequestError


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

        # Выполняем запрос к HH API
        try:
            parser = HHParser()
            vacancies = parser.get_vacancies(
                search_phrase,
                page=page,
                per_page=per_page
            )

            # Сериализуем результат
            vacancy_serializer = VacancySerializer(vacancies, many=True)

            return Response({
                'vacancies': vacancy_serializer.data,
                'count': len(vacancies),
                'page': page,
                'per_page': per_page
            })

                
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

