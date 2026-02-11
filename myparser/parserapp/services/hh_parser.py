"""
Сервис работы с HH API. Обратная совместимость — использует парсеры из parsers/.
"""
from parserapp.parsers import (
    HHParser,
    ParserTimeoutError,
    ParserRequestError,
)

# Алиасы для обратной совместимости
HHTimeoutError = ParserTimeoutError
HHRequestError = ParserRequestError

__all__ = ["HHParser", "HHTimeoutError", "HHRequestError"]
