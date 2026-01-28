from rest_framework import serializers
from .models import Vacancy


class VacancySearchSerializer(serializers.Serializer):
    search_phrase = serializers.CharField(
        required=True,
        help_text="Поисковая фраза для поиска вакансий"
    )
    page = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        help_text="Номер страницы"
    )
    per_page = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        help_text="Количество вакансий на странице (от 1 до 100)"
    )


class VacancySerializer(serializers.Serializer):
    """Сериализатор для вакансий из API (словари)"""
    title = serializers.CharField()
    company_name = serializers.CharField()
    description = serializers.CharField()
    salary_from = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    salary_to = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    currency = serializers.CharField(allow_null=True, allow_blank=True)
    work_mode = serializers.CharField(allow_null=True, allow_blank=True)
    location = serializers.CharField(allow_null=True)
    url = serializers.URLField()
    external_id = serializers.CharField()
    source = serializers.CharField()


class VacancyModelSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Vacancy из БД"""
    class Meta:
        model = Vacancy
        fields = [
            'id', 'title', 'company_name', 'description', 
            'salary_from', 'salary_to', 'currency', 'work_mode',
            'location', 'url', 'external_id', 'source',
            'posted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


def _parse_work_mode(item):
    """
    Парсит режим работы из ответа API HH.ru.
    Проверяет поле schedule.id для определения удалённой работы.
    """
    schedule = item.get("schedule") or {}
    schedule_id = schedule.get("id", "")
    
    # Если указана удалённая работа
    if schedule_id == "remote":
        return "remote"
    
    # Проверяем, есть ли информация о гибридном режиме
    # (можно определить по наличию нескольких признаков)
    # Пока упрощённо: если не remote, то office
    # В будущем можно доработать для определения гибрида
    if schedule_id:
        return "office"
    
    return None


def vacancy_from_hh(item):
    salary = item.get("salary") or {}
    employer = item.get("employer") or {}
    area = item.get("area") or {}
    snippet = item.get("snippet") or {}

    return {
        "title": item.get("name", ""),
        "company_name": employer.get("name", ""),
        "description": snippet.get("responsibility", ""),
        "salary_from": salary.get("from"),
        "salary_to": salary.get("to"),
        "currency": salary.get("currency"),
        "work_mode": _parse_work_mode(item),
        "location": area.get("name", ""),
        "url": item.get("alternate_url", ""),
        "external_id": item.get("id", ""),
        "source": "HH.ru",
    }