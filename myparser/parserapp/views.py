from django.http import JsonResponse
from django.views import View
import json
from .services.hh_parser import HHParser


class VacancySearchView(View):
    def get(self, request):
        #Получаем поисковую фразу из query-параметра или тела запроса
        search_phrase = request.GET.get('search_phrase')
        page = int(request.GET.get('page', 0))
        per_page = int(request.GET.get('per_page', 20))
        if not search_phrase:
            try:
                data = json.loads(request.body)
                search_phrase = data.get('search_phrase')
            except Exception:
                return JsonResponse({'error': "search_phrase is required"}, status=400)
        if not search_phrase:
            return JsonResponse({'error': "search_phrase is required"}, status=400)


        parser = HHParser()
        vacancies = parser.get_vacancies(search_phrase, page=page, per_page=per_page)
        return JsonResponse({'vacancies': vacancies}, safe=False)
