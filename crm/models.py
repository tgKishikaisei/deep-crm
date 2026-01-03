from django.db import models

# Create your models here.

from django.db import models
from django.conf import settings

from simple_history.models import HistoricalRecords

class Client(models.Model):
    company_name = models.CharField(max_length=255,
                                    verbose_name="Названия компании")
    contact_person = models.CharField(max_length=255,
                                     verbose_name="Контактное лицо")
    email = models.EmailField(unique=True,
                              verbose_name="Email")
    phone = models.CharField(max_length=20,
                             verbose_name="Телефон")
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name="Дата создания")
    update_at = models.DateTimeField(auto_now=True,
                                     verbose_name="Дата обновления")

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients',
        verbose_name='Менеджер'
    )

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ['-created_at']

    def __str__(self):
        return self.company_name


class Deal(models.Model):
    class Stage(models.TextChoices):
        NEW = "NEW", "Новая"
        IN_PROGRESS = "IN_PROGRESS", "В работе"
        WON = "WON", "Успешно закрыта"
        LOST = "LOST", "Не успешно закрыта"

    client = models.ForeignKey(Client,
                               on_delete=models.CASCADE,
                               related_name="deals",
                               verbose_name="Клиент")
    title = models.CharField(max_length=255,
                             verbose_name="Название сделки")
    amount = models.DecimalField(max_digits=10,
                                 decimal_places=2,
                                 verbose_name="Сумма")
    stage = models.CharField(max_length=20,
                             choices=Stage.choices,
                             default=Stage.NEW,
                             verbose_name="Стадия")
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deals',
        verbose_name='Менеджер'
    )
    created_at = models.DateTimeField(auto_now_add=True,
                                      verbose_name="Дата создания")
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Сделка"
        verbose_name_plural = "Сделки"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.client.company_name}"


class Task(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Ожидает"
        COMPLETED = "COMPLETED", "Выполнено"

    deal = models.ForeignKey(Deal,
                             on_delete=models.CASCADE,
                             related_name="tasks",
                             verbose_name="Сделка")
    title = models.CharField(max_length=255,
                             verbose_name="Название задачи")
    description = models.TextField(verbose_name="Описание")
    due_date = models.DateTimeField(verbose_name="Срок выполнения")
    status = models.CharField(max_length=20,
                              choices=Status.choices,
                              default=Status.PENDING,
                              verbose_name="Статус")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name="Исполнитель"
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["due_date"]

    def __str__(self):
        return self.title

