from django.http import JsonResponse
from django.views import View
import json
from .services.hh_parser import HHParser, HHTimeoutError, HHRequestError


class VacancySearchView(View):
    def get(self, request):
        # Получаем поисковую фразу из query-параметра или тела запроса
        search_phrase = request.GET.get('search_phrase')
        
        # Пытаемся получить из тела запроса, если не нашли в query
        if not search_phrase and request.body:
            try:
                data = json.loads(request.body)
                search_phrase = data.get('search_phrase')
            except (json.JSONDecodeError, ValueError):
                return JsonResponse(
                    {'error': 'Invalid JSON in request body'},
                    status=400
                )
        
        # Валидация обязательного параметра
        if not search_phrase:
            return JsonResponse(
                {'error': 'search_phrase is required'},
                status=400
            )
        
        # Валидация и получение page
        try:
            page = int(request.GET.get('page', 0))
            if page < 0:
                return JsonResponse(
                    {'error': 'page must be non-negative integer'},
                    status=400
                )
        except (ValueError, TypeError):
            return JsonResponse(
                {'error': 'page must be a valid integer'},
                status=400
            )
        
        # Валидация и получение per_page
        try:
            per_page = int(request.GET.get('per_page', 20))
            if per_page < 1 or per_page > 100:
                return JsonResponse(
                    {'error': 'per_page must be between 1 and 100'},
                    status=400
                )
        except (ValueError, TypeError):
            return JsonResponse(
                {'error': 'per_page must be a valid integer'},
                status=400
            )
        
        # Выполняем запрос к HH API
        try:
            parser = HHParser()
            vacancies = parser.get_vacancies(
                search_phrase,
                page=page,
                per_page=per_page
            )
            return JsonResponse({'vacancies': vacancies}, safe=False)
        except HHTimeoutError as e:
            return JsonResponse(
                {'error': 'Request to HeadHunter API timed out', 'details': str(e)},
                status=504
            )
        except HHRequestError as e:
            # Если HH вернул ошибку, пробрасываем её статус или 502
            status_code = e.status_code if e.status_code else 502
            return JsonResponse(
                {'error': 'Error communicating with HeadHunter API', 'details': str(e)},
                status=status_code
            )
        except Exception as e:
            return JsonResponse(
                {'error': 'Internal server error', 'details': str(e)},
                status=500
            )
