from django.db import transaction
from django.utils import timezone
from parserapp.models import Vacancy
from parserapp.utils.logger import get_logger

logger = get_logger(__name__)


class VacancyService:
    """Сервис для работы с вакансиями в базе данных"""

    @staticmethod
    @transaction.atomic
    def save_vacancies(vacancies_data, update_existing=False):
        """
        Сохраняет вакансии в базу данных.
        
        Args:
            vacancies_data: Список словарей с данными вакансий
            update_existing: Если True, обновляет существующие вакансии по external_id или url
        
        Returns:
            dict: Статистика сохранения {
                'total': общее количество,
                'created': создано новых,
                'updated': обновлено существующих,
                'skipped': пропущено (дубликаты)
            }
        """
        if not vacancies_data:
            return {
                'total': 0,
                'created': 0,
                'updated': 0,
                'skipped': 0
            }

        stats = {
            'total': len(vacancies_data),
            'created': 0,
            'updated': 0,
            'skipped': 0
        }

        for vacancy_data in vacancies_data:
            try:
                # Пытаемся найти существующую вакансию по external_id или url
                existing_vacancy = None
                
                external_id = vacancy_data.get('external_id')
                url = vacancy_data.get('url')
                
                if external_id:
                    try:
                        existing_vacancy = Vacancy.objects.get(external_id=external_id)
                    except Vacancy.DoesNotExist:
                        pass
                
                # Если не нашли по external_id, пробуем по url
                if not existing_vacancy and url:
                    try:
                        existing_vacancy = Vacancy.objects.get(url=url)
                    except Vacancy.DoesNotExist:
                        pass
                    except Vacancy.MultipleObjectsReturned:
                        # Если несколько вакансий с одинаковым url, берем первую
                        existing_vacancy = Vacancy.objects.filter(url=url).first()

                if existing_vacancy:
                    if update_existing:
                        # Обновляем существующую вакансию
                        for field, value in vacancy_data.items():
                            if hasattr(existing_vacancy, field) and field not in ['external_id', 'created_at']:
                                setattr(existing_vacancy, field, value)
                        
                        existing_vacancy.updated_at = timezone.now()
                        existing_vacancy.save()
                        stats['updated'] += 1
                        logger.debug(f"Обновлена вакансия: {existing_vacancy.title} (ID: {existing_vacancy.external_id})")
                    else:
                        # Пропускаем дубликат
                        stats['skipped'] += 1
                        logger.debug(f"Пропущена дублирующая вакансия: {vacancy_data.get('title')} (ID: {external_id})")
                else:
                    # Создаем новую вакансию
                    vacancy = Vacancy(**vacancy_data)
                    vacancy.full_clean()  # Валидация данных
                    vacancy.save()
                    stats['created'] += 1
                    logger.debug(f"Создана новая вакансия: {vacancy.title} (ID: {vacancy.external_id})")

            except Exception as e:
                logger.error(f"Ошибка при сохранении вакансии {vacancy_data.get('title', 'Unknown')}: {e}")
                stats['skipped'] += 1
                continue

        logger.info(
            f"Сохранение вакансий завершено. "
            f"Всего: {stats['total']}, "
            f"Создано: {stats['created']}, "
            f"Обновлено: {stats['updated']}, "
            f"Пропущено: {stats['skipped']}"
        )

        return stats

    @staticmethod
    def get_vacancy_by_external_id(external_id):
        """Получает вакансию по external_id"""
        try:
            return Vacancy.objects.get(external_id=external_id)
        except Vacancy.DoesNotExist:
            return None

    @staticmethod
    def get_vacancy_by_url(url):
        """Получает вакансию по URL"""
        try:
            return Vacancy.objects.get(url=url)
        except Vacancy.DoesNotExist:
            return None
        except Vacancy.MultipleObjectsReturned:
            return Vacancy.objects.filter(url=url).first()
