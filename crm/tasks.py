import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_congrats_email(email, deal_title):
    """Письмо клиенту о закрытой сделке (фоновая задача Celery)."""
    send_mail(
        subject='Поздравляем с успешной сделкой!',
        message=f'Сделка "{deal_title}" успешно закрыта! Вы - космос! 🚀',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
    logger.info("Congrats email sent for deal %r", deal_title)
    return "sent"
