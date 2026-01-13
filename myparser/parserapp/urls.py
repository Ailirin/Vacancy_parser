from django.urls import path
from .views import VacancySearchView


urlpatterns = [
    path('search/', VacancySearchView.as_view(), name='vacancy_search'),
]