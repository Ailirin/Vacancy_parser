import os
import requests
from requests.exceptions import RequestException, Timeout
from parserapp.serializers import vacancy_from_hh


class HHParser:
    BASE_URL = "https://api.hh.ru/vacancies"

    # HH может блокировать User-Agent. Разрешаем переопределять его через переменную окружения HH_USER_AGENT.
    HEADERS = {
        "User-Agent": os.getenv(
            "HH_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (+contact@example.com)",
        ),
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    def get_vacancies(self, query, page=0, per_page=20):
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
                timeout=10
            )
            print(f"HH response status={response.status_code}, body={response.text}")
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            print(f"HH request ok: query={query} page={page} per_page={per_page} items={len(items)}")
            if items:
                print(f"HH first item sample: {items[0]}")
            return self.parse_response(data)
        except Timeout:
            print(f"Запрос к HH.ru превысил время ожидания: query={query}")
            return []
        except RequestException as e:
            if getattr(e, "response", None) is not None:
                print(f"HH error {e.response.status_code}: {e.response.text}")
            print(f"Ошибка при запросе к HH.ru: {e}")
            return []

    def parse_response(self, data):
        return [vacancy_from_hh(item) for item in data.get("items", [])]