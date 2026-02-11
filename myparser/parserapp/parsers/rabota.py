"""
Парсер вакансий rabota.by — Беларусь.
API совместим с HH (api.rabota.by).
"""
from typing import List

from .hh import HHParser, parse_hh_item


def _adapt_rabota_item(item: dict) -> dict:
    """Подменяет alternate_url на rabota.by."""
    adapted = item.copy()
    url = adapted.get("alternate_url", "")
    if url and "hh.ru" in url:
        adapted["alternate_url"] = url.replace("hh.ru", "rabota.by")
    return adapted


class RabotaByParser(HHParser):
    """Парсер вакансий rabota.by (Беларусь)."""
    source = "rabota.by"
    BASE_URL = "https://api.rabota.by/vacancies"

    def parse_response(self, data: dict) -> List[dict]:
        items = data.get("items", [])
        adapted = [_adapt_rabota_item(i) for i in items]
        return [parse_hh_item(item, self.source) for item in adapted]
