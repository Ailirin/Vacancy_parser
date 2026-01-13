from django.db import models
from django.core.exceptions import ValidationError


class Vacancy(models.Model):
    WORK_MODE_CHOICES = [
        ('office', 'В офисе'),
        ('remote', 'Удаленно'),
        ('hybrid', 'Гибрид'),
    ]

    title = models.CharField(max_length=255, verbose_name='Название вакансии')
    description = models.TextField(blank=True, default="", verbose_name='Описание')
    company_name = models.CharField(max_length=255, verbose_name='Название компании')
    location = models.CharField(max_length=255, verbose_name='Местоположение')
    salary_from = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Зарплата от')
    salary_to = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Зарплата до')
    posted_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата публикации')
    currency = models.CharField(max_length=10, null=True, blank=True, verbose_name="Валюта")
    work_mode = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, null=True, blank=True, verbose_name="Режим работы")
    url = models.URLField(max_length=500, unique=True, verbose_name="Ссылка на вакансию")
    external_id = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="ID вакансии")
    source = models.CharField(max_length=50, default="HH.ru", verbose_name="Источник")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['company_name']),
            models.Index(fields=['location']),
        ]
        ordering = ['-posted_at']

    def __str__(self):
        return f"{self.title} at {self.company_name}"

    def clean(self):
        super().clean()
        if self.salary_from and self.salary_to and self.salary_from > self.salary_to:
            raise ValidationError('Зарплата "от" не может быть больше зарплаты "до".')

