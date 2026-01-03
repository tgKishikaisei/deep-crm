# crm/tasks.py
from celery import shared_task
from django.core.mail import send_mail
import time


@shared_task
def send_congrats_email(email, deal_title):
    """
    Задача отправляет письмо.
    Мы добавим искусственную задержку (sleep), чтобы ты увидел,
    что сайт НЕ виснет, пока письмо "отправляется".
    """
    print(f"--> НАЧИНАЮ ОТПРАВКУ ПИСЬМА для {email}...")

    # Имитация долгой работы (5 секунд)
    time.sleep(5)

    send_mail(
        subject='Поздравляем с успешной сделкой!',
        message=f'Сделка "{deal_title}" успешно закрыта! Вы - космос! 🚀',
        from_email='admin@deepcrm.com',
        recipient_list=[email],
    )

    return f"Email sent to {email}"