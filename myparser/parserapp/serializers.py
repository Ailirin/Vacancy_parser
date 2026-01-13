def _parse_work_mode(item):
    """
    Парсит режим работы из ответа API HH.ru.
    Проверяет поле schedule.id для определения удалённой работы.
    """
    schedule = item.get("schedule") or {}
    schedule_id = schedule.get("id", "")
    
    # Если указана удалённая работа
    if schedule_id == "remote":
        return "remote"
    
    # Проверяем, есть ли информация о гибридном режиме
    # (можно определить по наличию нескольких признаков)
    # Пока упрощённо: если не remote, то office
    # В будущем можно доработать для определения гибрида
    if schedule_id:
        return "office"
    
    return None


def vacancy_from_hh(item):
    salary = item.get("salary") or {}
    employer = item.get("employer") or {}
    area = item.get("area") or {}
    snippet = item.get("snippet") or {}

    return {
        "title": item.get("name", ""),
        "company_name": employer.get("name", ""),
        "description": snippet.get("responsibility", ""),
        "salary_from": salary.get("from"),
        "salary_to": salary.get("to"),
        "currency": salary.get("currency"),
        "work_mode": _parse_work_mode(item),
        "location": area.get("name", ""),
        "url": item.get("alternate_url", ""),
        "external_id": item.get("id", ""),
        "source": "HH.ru",
    }