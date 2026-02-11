"""
Парсер вакансий HeadHunter Belarus (api.hh.by) — Беларусь.
Структура API совпадает с HH.ru.
"""
from .hh import HHParser


class HHByParser(HHParser):
    """Парсер вакансий HeadHunter Belarus (РБ)."""
    source = "HH.by"
    BASE_URL = "https://api.hh.by/vacancies"
