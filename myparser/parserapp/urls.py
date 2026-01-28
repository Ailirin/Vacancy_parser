from django.urls import path
from .views import VacancySearchView, VacancyListView


urlpatterns = [
    path('search/', VacancySearchView.as_view(), name='vacancy_search'),
    path('vacancies/', VacancyListView.as_view(), name='vacancy_list'),
]