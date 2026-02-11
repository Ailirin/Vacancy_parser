"""
Базовый интерфейс для парсеров вакансий.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


# Единый формат вакансии для всех источников
ParsedVacancy = Dict[str, Any]


class ParserError(Exception):
    """Базовое исключение для парсеров."""
    pass


class ParserTimeoutError(ParserError):
    """Исключение при таймауте запроса."""
    pass


class ParserRequestError(ParserError):
    """Исключение при ошибке HTTP-запроса."""
    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class VacancyParser(ABC):
    """Абстрактный базовый класс парсера вакансий."""

    source: str = ""

    @abstractmethod
    def get_vacancies(self, query: str, page: int = 0, per_page: int = 20) -> List[ParsedVacancy]:
        """Получить вакансии по поисковому запросу."""
        pass
