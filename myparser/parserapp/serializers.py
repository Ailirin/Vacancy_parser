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
    source = serializers.ChoiceField(
        required=False,
        default="hh",
        choices=[
            ("hh", "HH.ru — Россия"),
            ("hh_by", "HH.by — Беларусь"),
            ("superjob", "SuperJob.ru — Россия"),
            ("rabota", "rabota.by — Беларусь"),
            ("all", "Все источники (агрегация)"),
        ],
        help_text="Источник вакансий: hh, hh_by, superjob, rabota, all"
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

