"""
Парсер вакансий SuperJob (api.superjob.ru) — Россия.
Требуется X-Api-App-Id (SUPERJOB_API_KEY в .env).
"""
import os
import requests
from requests.exceptions import RequestException, Timeout
from typing import List, Dict, Any

from .base import VacancyParser, ParsedVacancy, ParserTimeoutError, ParserRequestError


def _parse_work_mode_sj(item: Dict[str, Any]) -> str | None:
    """place_of_work: 1=офис, 2=на дому, 3=разъездной."""
    place = item.get("place_of_work") or {}
    pid = place.get("id") if isinstance(place, dict) else None
    if pid == 2:
        return "remote"
    if pid == 3:
        return "hybrid"
    if pid == 1:
        return "office"
    return None


def _normalize_currency_sj(currency: str | None) -> str | None:
    if not currency:
        return None
    c = currency.upper()
    if c == "RUB":
        return "RUB"
    if c in ("UAH", "UZS"):
        return c
    return c


def parse_superjob_item(item: Dict[str, Any], source: str = "SuperJob.ru") -> ParsedVacancy:
    """Преобразует элемент ответа SuperJob API в единый формат."""
    town = item.get("town") or {}
    town_name = town.get("title", "") if isinstance(town, dict) else ""

    work = item.get("work") or ""
    candidat = item.get("candidat") or ""
    compensation = item.get("compensation") or ""
    description = " ".join(filter(None, [work, candidat, compensation])).strip()

    currency_raw = item.get("currency")
    currency = _normalize_currency_sj(currency_raw) if currency_raw else None

    return {
        "title": item.get("profession", ""),
        "company_name": item.get("firm_name", ""),
        "description": description,
        "salary_from": item.get("payment_from") or None,
        "salary_to": item.get("payment_to") or None,
        "currency": currency,
        "work_mode": _parse_work_mode_sj(item),
        "location": town_name,
        "url": item.get("link", ""),
        "external_id": str(item.get("id", "")),
        "source": source,
    }


class SuperJobParser(VacancyParser):
    """Парсер вакансий SuperJob (Россия)."""
    source = "SuperJob.ru"
    BASE_URL = "https://api.superjob.ru/2.0/vacancies/"

    def __init__(self):
        api_key = os.getenv("SUPERJOB_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "SUPERJOB_API_KEY не задан. Зарегистрируйте приложение на https://api.superjob.ru/register/"
            )
        self.headers = {
            "X-Api-App-Id": api_key,
            "Accept": "application/json",
        }

    def get_vacancies(self, query: str, page: int = 0, per_page: int = 20) -> List[ParsedVacancy]:
        params = {
            "keyword": query,
            "page": page,
            "count": min(per_page, 100),
        }
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("objects", [])
            return [parse_superjob_item(item, self.source) for item in items]
        except Timeout as e:
            raise ParserTimeoutError(f"Запрос к {self.source} превысил время ожидания: {e}")
        except RequestException as e:
            status_code = getattr(e, "response", None) and getattr(e.response, "status_code", None)
            raise ParserRequestError(
                f"Ошибка при запросе к {self.source}: {e}",
                status_code=status_code,
            )
