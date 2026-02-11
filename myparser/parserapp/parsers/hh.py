"""
Парсер вакансий HeadHunter (api.hh.ru) — Россия.
"""
import os
import requests
from requests.exceptions import RequestException, Timeout
from typing import List, Dict, Any

from .base import VacancyParser, ParsedVacancy, ParserTimeoutError, ParserRequestError


def _parse_work_mode(item: Dict[str, Any]) -> str | None:
    """
    Парсит режим работы из ответа API HH.ru.
    schedule.id: remote, fullDay, flyAndDrive, flexible и т.д.
    work_format: ON_SITE, REMOTE, HYBRID
    """
    # Приоритет: work_format (новый формат) -> schedule
    work_format = item.get("work_format") or []
    if isinstance(work_format, list):
        format_ids = {f.get("id") for f in work_format if isinstance(f, dict)}
        if "REMOTE" in format_ids and "ON_SITE" not in format_ids and "HYBRID" not in format_ids:
            return "remote"
        if "HYBRID" in format_ids:
            return "hybrid"

    schedule = item.get("schedule") or {}
    schedule_id = schedule.get("id", "")

    if schedule_id == "remote":
        return "remote"
    if schedule_id in ("flexible", "flyAndDrive"):
        return "hybrid"
    if schedule_id:
        return "office"

    return None


def _normalize_currency(currency: str | None) -> str | None:
    """Нормализация валюты: RUR -> RUB."""
    if not currency:
        return None
    return "RUB" if currency.upper() in ("RUR", "RUB") else currency.upper()


def parse_hh_item(item: Dict[str, Any], source: str = "HH.ru") -> ParsedVacancy:
    """Преобразует элемент ответа HH API в единый формат."""
    salary = item.get("salary") or {}
    employer = item.get("employer") or {}
    area = item.get("area") or {}
    snippet = item.get("snippet") or {}

    desc_parts = []
    if snippet.get("responsibility"):
        desc_parts.append(snippet["responsibility"])
    if snippet.get("requirement"):
        desc_parts.append(snippet["requirement"])
    description = " ".join(desc_parts).strip()

    currency_raw = salary.get("currency")
    currency = _normalize_currency(currency_raw) if currency_raw else None

    return {
        "title": item.get("name", ""),
        "company_name": employer.get("name", ""),
        "description": description,
        "salary_from": salary.get("from"),
        "salary_to": salary.get("to"),
        "currency": currency,
        "work_mode": _parse_work_mode(item),
        "location": area.get("name", ""),
        "url": item.get("alternate_url", ""),
        "external_id": str(item.get("id", "")),
        "source": source,
    }


class HHParser(VacancyParser):
    """Парсер вакансий HeadHunter (Россия)."""
    source = "HH.ru"
    BASE_URL = "https://api.hh.ru/vacancies"

    HEADERS = {
        "User-Agent": os.getenv(
            "HH_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (+contact@example.com)",
        ),
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def get_vacancies(self, query: str, page: int = 0, per_page: int = 20) -> List[ParsedVacancy]:
        params = {
            "text": query,
            "page": page,
            "per_page": per_page,
        }
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return self.parse_response(data)
        except Timeout as e:
            raise ParserTimeoutError(f"Запрос к {self.source} превысил время ожидания: {e}")
        except RequestException as e:
            status_code = getattr(e.response, "status_code", None) if e.response else None
            raise ParserRequestError(
                f"Ошибка при запросе к {self.source}: {e}",
                status_code=status_code,
            )

    def parse_response(self, data: dict) -> List[ParsedVacancy]:
        """Преобразует ответ API в список вакансий. Можно переопределить в наследниках."""
        return [parse_hh_item(item, self.source) for item in data.get("items", [])]
