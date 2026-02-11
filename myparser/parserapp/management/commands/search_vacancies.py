from django.core.management.base import BaseCommand
from parserapp.parsers import PARSERS, ParserTimeoutError, ParserRequestError
from parserapp.services.vacancy_service import VacancyService


class Command(BaseCommand):
    help = 'Интерактивный поиск вакансий с фильтрацией и сортировкой'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query',
            type=str,
            help='Поисковый запрос (если не указан, будет запрошен интерактивно)',
        )
        parser.add_argument(
            '--source',
            type=str,
            default='hh',
            choices=['hh', 'hh_by', 'superjob', 'rabota', 'all'],
            help='Источник: hh (РФ), hh_by (РБ), superjob (РФ), rabota (РБ), all',
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Сохранить найденные вакансии в базу данных',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновить существующие вакансии при сохранении (работает только с --save)',
        )

    def _get_parser(self, source):
        if source == 'all':
            from parserapp.views import _aggregate_from_all_sources
            return ('aggregate', _aggregate_from_all_sources)
        try:
            ParserClass = PARSERS.get(source)
            if not ParserClass:
                return None
            return ParserClass()
        except ValueError:
            return None

    def handle(self, *args, **options):
        source = options.get('source', 'hh')
        vac_parser = self._get_parser(source)
        if not vac_parser:
            self.stdout.write(self.style.ERROR(f'Не удалось создать парсер для {source}'))
            return

        # 1. Запрос поисковой фразы
        search_query = options.get('query')
        if not search_query:
            search_query = input("\n🔍 Введите поисковый запрос (например: python developer): ").strip()
            if not search_query:
                self.stdout.write(self.style.ERROR('Поисковый запрос не может быть пустым!'))
                return

        # 2. Запрос количества результатов
        try:
            per_page = int(input("📊 Сколько вакансий показать? (по умолчанию 20): ") or "20")
        except ValueError:
            per_page = 20

        # 3. Поиск вакансий
        self.stdout.write(self.style.SUCCESS(f'\n🔎 Ищу вакансии по запросу "{search_query}" ({source})...'))
        try:
            if isinstance(vac_parser, tuple) and vac_parser[0] == 'aggregate':
                vacancies = vac_parser[1](search_query, 0, per_page)
            else:
                vacancies = vac_parser.get_vacancies(search_query, page=0, per_page=per_page)
        except (ParserTimeoutError, ParserRequestError) as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при запросе: {e}'))
            return

        if not vacancies:
            self.stdout.write(self.style.WARNING('Вакансии не найдены.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Найдено вакансий: {len(vacancies)}\n'))
        
        # 4. Выбор фильтров
        filters = self._ask_filters()
        
        # 5. Применение фильтров
        filtered_vacancies = self._apply_filters(vacancies, filters)
        
        if not filtered_vacancies:
            self.stdout.write(self.style.WARNING('Нет вакансий, соответствующих выбранным фильтрам.'))
            return
        
        # 6. Выбор сортировки
        sort_option = self._ask_sort_option()
        
        # 7. Сортировка
        sorted_vacancies = self._sort_vacancies(filtered_vacancies, sort_option)
        
        # 8. Сохранение в БД (если указано)
        if options.get('save'):
            self._save_to_database(sorted_vacancies, update_existing=options.get('update', False))
        
        # 9. Вывод результатов
        self._display_vacancies(sorted_vacancies)
        
        # 10. Дополнительные действия
        self._ask_additional_actions(sorted_vacancies)

    def _ask_filters(self):
        """Запрашивает фильтры у пользователя"""
        filters = {}
        
        self.stdout.write(self.style.WARNING('\n📋 Фильтры (нажмите Enter, чтобы пропустить):'))
        
        # Фильтр по режиму работы
        work_mode = input("💼 Режим работы (office/remote/hybrid/любой): ").strip().lower()
        if work_mode in ['office', 'remote', 'hybrid']:
            filters['work_mode'] = work_mode
        
        # Фильтр по городу
        location = input("📍 Город (например: Москва): ").strip()
        if location:
            filters['location'] = location
        
        # Фильтр по минимальной зарплате
        salary_min = input("💰 Минимальная зарплата (число): ").strip()
        if salary_min:
            try:
                filters['salary_min'] = float(salary_min)
            except ValueError:
                pass
        
        # Фильтр по валюте
        currency = input("💵 Валюта (RUR/USD/EUR/любая): ").strip().upper()
        if currency:
            filters['currency'] = currency
        
        return filters

    def _apply_filters(self, vacancies, filters):
        """Применяет фильтры к списку вакансий"""
        filtered = vacancies
        
        if 'work_mode' in filters:
            filtered = [v for v in filtered if v.get('work_mode') == filters['work_mode']]
        
        if 'location' in filters:
            location_lower = filters['location'].lower()
            filtered = [v for v in filtered if location_lower in v.get('location', '').lower()]
        
        if 'salary_min' in filters:
            filtered = [v for v in filtered if self._check_salary(v, filters['salary_min'])]
        
        if 'currency' in filters:
            filtered = [v for v in filtered if v.get('currency', '').upper() == filters['currency']]
        
        return filtered

    def _check_salary(self, vacancy, min_salary):
        """Проверяет, соответствует ли зарплата минимальному значению"""
        salary_from = vacancy.get('salary_from')
        salary_to = vacancy.get('salary_to')
        
        if salary_from and salary_from >= min_salary:
            return True
        if salary_to and salary_to >= min_salary:
            return True
        return False

    def _ask_sort_option(self):
        """Запрашивает опцию сортировки"""
        self.stdout.write(self.style.WARNING('\n🔄 Сортировка:'))
        self.stdout.write('1. По зарплате (от большей к меньшей)')
        self.stdout.write('2. По зарплате (от меньшей к большей)')
        self.stdout.write('3. По названию компании (А-Я)')
        self.stdout.write('4. По названию вакансии (А-Я)')
        self.stdout.write('5. Без сортировки')
        
        choice = input("\nВыберите вариант (1-5, по умолчанию 5): ").strip() or "5"
        return choice

    def _sort_vacancies(self, vacancies, sort_option):
        """Сортирует вакансии по выбранному критерию"""
        if sort_option == "1":
            # По зарплате (от большей к меньшей)
            return sorted(vacancies, key=lambda v: self._get_max_salary(v), reverse=True)
        elif sort_option == "2":
            # По зарплате (от меньшей к большей)
            return sorted(vacancies, key=lambda v: self._get_min_salary(v))
        elif sort_option == "3":
            # По названию компании
            return sorted(vacancies, key=lambda v: v.get('company_name', '').lower())
        elif sort_option == "4":
            # По названию вакансии
            return sorted(vacancies, key=lambda v: v.get('title', '').lower())
        else:
            # Без сортировки
            return vacancies

    def _get_max_salary(self, vacancy):
        """Возвращает максимальную зарплату для сортировки"""
        salary_to = vacancy.get('salary_to')
        salary_from = vacancy.get('salary_from')
        if salary_to:
            return float(salary_to)
        if salary_from:
            return float(salary_from)
        return 0

    def _get_min_salary(self, vacancy):
        """Возвращает минимальную зарплату для сортировки"""
        salary_from = vacancy.get('salary_from')
        salary_to = vacancy.get('salary_to')
        if salary_from:
            return float(salary_from)
        if salary_to:
            return float(salary_to)
        return float('inf')

    def _display_vacancies(self, vacancies):
        """Выводит список вакансий"""
        self.stdout.write(self.style.SUCCESS(f'\n📋 Найдено вакансий после фильтрации: {len(vacancies)}\n'))
        self.stdout.write('=' * 80)
        
        for idx, vacancy in enumerate(vacancies, 1):
            self.stdout.write(f'\n{idx}. {vacancy.get("title", "Без названия")}')
            self.stdout.write(f'   Компания: {vacancy.get("company_name", "Не указана")}')
            
            # Зарплата
            salary_from = vacancy.get('salary_from')
            salary_to = vacancy.get('salary_to')
            currency = vacancy.get('currency', '')
            if salary_from or salary_to:
                if salary_from and salary_to:
                    salary_str = f'{int(salary_from):,} - {int(salary_to):,} {currency}'
                elif salary_from:
                    salary_str = f'от {int(salary_from):,} {currency}'
                elif salary_to:
                    salary_str = f'до {int(salary_to):,} {currency}'
                self.stdout.write(f'   💰 Зарплата: {salary_str}')
            else:
                self.stdout.write('   💰 Зарплата: не указана')
            
            # Режим работы
            work_mode = vacancy.get('work_mode')
            if work_mode:
                mode_names = {'office': 'В офисе', 'remote': 'Удалённо', 'hybrid': 'Гибрид'}
                self.stdout.write(f'   💼 Режим: {mode_names.get(work_mode, work_mode)}')
            
            # Локация
            location = vacancy.get('location')
            if location:
                self.stdout.write(f'   📍 Локация: {location}')
            
            # Описание
            description = vacancy.get('description', '')
            if description:
                desc_short = description[:100] + '...' if len(description) > 100 else description
                self.stdout.write(f'   📝 Описание: {desc_short}')
            
            # Ссылка
            url = vacancy.get('url')
            if url:
                self.stdout.write(f'   🔗 Ссылка: {url}')
            
            self.stdout.write('-' * 80)

    def _save_to_database(self, vacancies, update_existing=False):
        """Сохраняет вакансии в базу данных"""
        if not vacancies:
            return
        
        self.stdout.write(self.style.WARNING('\n💾 Сохранение вакансий в базу данных...'))
        
        try:
            service = VacancyService()
            stats = service.save_vacancies(vacancies, update_existing=update_existing)
            
            self.stdout.write(self.style.SUCCESS('\n✅ Сохранение завершено!'))
            self.stdout.write(f'   📊 Всего обработано: {stats["total"]}')
            self.stdout.write(f'   ✨ Создано новых: {stats["created"]}')
            if update_existing:
                self.stdout.write(f'   🔄 Обновлено существующих: {stats["updated"]}')
            self.stdout.write(f'   ⏭️  Пропущено (дубликаты): {stats["skipped"]}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Ошибка при сохранении в БД: {e}'))

    def _ask_additional_actions(self, vacancies):
        """Запрашивает дополнительные действия"""
        if not vacancies:
            return
        
        self.stdout.write(self.style.WARNING('\n🎯 Дополнительные действия:'))
        self.stdout.write('1. Показать детали конкретной вакансии')
        self.stdout.write('2. Сохранить результаты в файл')
        self.stdout.write('3. Сохранить в базу данных')
        self.stdout.write('4. Выход')
        
        choice = input("\nВыберите действие (1-4): ").strip()
        
        if choice == "1":
            self._show_vacancy_details(vacancies)
        elif choice == "2":
            self._save_to_file(vacancies)
        elif choice == "3":
            update = input("Обновить существующие вакансии? (y/n, по умолчанию n): ").strip().lower() == 'y'
            self._save_to_database(vacancies, update_existing=update)
        else:
            self.stdout.write(self.style.SUCCESS('\n👋 До свидания!'))

    def _show_vacancy_details(self, vacancies):
        """Показывает детали выбранной вакансии"""
        try:
            idx = int(input(f"\nВведите номер вакансии (1-{len(vacancies)}): ").strip())
            if 1 <= idx <= len(vacancies):
                vacancy = vacancies[idx - 1]
                self.stdout.write(self.style.SUCCESS('\n' + '=' * 80))
                self.stdout.write(f'\n📌 {vacancy.get("title", "Без названия")}')
                self.stdout.write(f'🏢 Компания: {vacancy.get("company_name", "Не указана")}')
                self.stdout.write(f'🌐 Источник: {vacancy.get("source", "HH.ru")}')
                self.stdout.write(f'🆔 ID: {vacancy.get("external_id", "Не указан")}')
                
                # Полное описание
                description = vacancy.get("description", "")
                if description:
                    self.stdout.write(f'\n📝 Описание:\n{description}')
                
                # Ссылка
                url = vacancy.get("url", "")
                if url:
                    self.stdout.write(f'\n🔗 Ссылка: {url}')
                
                self.stdout.write('=' * 80)
            else:
                self.stdout.write(self.style.ERROR('Неверный номер вакансии!'))
        except ValueError:
            self.stdout.write(self.style.ERROR('Введите корректный номер!'))

    def _save_to_file(self, vacancies):
        """Сохраняет результаты в файл"""
        filename = input("\nВведите имя файла (по умолчанию vacancies.txt): ").strip() or "vacancies.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Результаты поиска вакансий\n")
                f.write(f"Всего найдено: {len(vacancies)}\n")
                f.write("=" * 80 + "\n\n")
                
                for idx, vacancy in enumerate(vacancies, 1):
                    f.write(f"{idx}. {vacancy.get('title', 'Без названия')}\n")
                    f.write(f"   Компания: {vacancy.get('company_name', 'Не указана')}\n")
                    
                    salary_from = vacancy.get('salary_from')
                    salary_to = vacancy.get('salary_to')
                    currency = vacancy.get('currency', '')
                    if salary_from or salary_to:
                        if salary_from and salary_to:
                            salary_str = f'{int(salary_from):,} - {int(salary_to):,} {currency}'
                        elif salary_from:
                            salary_str = f'от {int(salary_from):,} {currency}'
                        elif salary_to:
                            salary_str = f'до {int(salary_to):,} {currency}'
                        f.write(f"   Зарплата: {salary_str}\n")
                    
                    location = vacancy.get('location')
                    if location:
                        f.write(f"   Локация: {location}\n")
                    
                    url = vacancy.get('url')
                    if url:
                        f.write(f"   Ссылка: {url}\n")
                    
                    f.write("-" * 80 + "\n\n")
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Результаты сохранены в файл: {filename}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Ошибка при сохранении: {e}'))

