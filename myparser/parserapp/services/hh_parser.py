import os
import requests
from requests.exceptions import RequestException, Timeout
from parserapp.serializers import vacancy_from_hh


class HHParserError(Exception):
    """Базовое исключение для ошибок парсера HH"""
    pass


class HHTimeoutError(HHParserError):
    """Исключение при таймауте запроса к HH"""
    pass


class HHRequestError(HHParserError):
    """Исключение при ошибке запроса к HH"""
    def __init__(self, message, status_code=None):
        self.status_code = status_code
        super().__init__(message)


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
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            return self.parse_response(data)
        except Timeout as e:
            raise HHTimeoutError(f"Запрос к HH.ru превысил время ожидания: {e}")
        except RequestException as e:
            status_code = None
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
            raise HHRequestError(
                f"Ошибка при запросе к HH.ru: {e}",
                status_code=status_code
            )

    def parse_response(self, data):
        return [vacancy_from_hh(item) for item in data.get("items", [])]