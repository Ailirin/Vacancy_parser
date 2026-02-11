"""
Парсеры вакансий из различных источников (РФ, РБ).
Каждый парсер преобразует ответ внешнего API в единый формат.
"""
from .base import VacancyParser, ParsedVacancy, ParserError, ParserTimeoutError, ParserRequestError
from .hh import HHParser
from .hh_by import HHByParser
from .superjob import SuperJobParser
from .rabota import RabotaByParser

__all__ = [
    'VacancyParser',
    'ParsedVacancy',
    'ParserError',
    'ParserTimeoutError',
    'ParserRequestError',
    'HHParser',
    'HHByParser',
    'SuperJobParser',
    'RabotaByParser',
]

# Реестр парсеров по источнику
PARSERS = {
    'hh': HHParser,           # РФ
    'hh_by': HHByParser,      # РБ
    'superjob': SuperJobParser,  # РФ
    'rabota': RabotaByParser,    # РБ
}
