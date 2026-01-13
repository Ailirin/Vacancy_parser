from django.contrib import admin
from .models import Vacancy


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'company_name', 'location', 'salary_from', 'salary_to', 'currency', 'source', 'created_at')
    list_filter = ('source', 'work_mode', 'currency', 'created_at')
    search_fields = ('title', 'company_name', 'location', 'description')
    readonly_fields = ('created_at', 'updated_at')
