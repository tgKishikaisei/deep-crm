from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Кастомная модель пользователя
    Наследуется от AbstactUser, сохраняя все поля Django,
    не позволяя добовлять свои
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Администратор"
        MANAGER = "MANAGER", "Менеджер"

    role = models.CharField(
        max_length=50,
        choices=Role.choices,
        default=Role.MANAGER,
        verbose_name="Роль"
    )

    # TODO Здесь можно другие поля потом, например
    #  Вроде phone_number = models.CharField(max_length=20, blank=True, verbose_name="Номер телефона")

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username
