from django.test import TestCase
from django.urls import reverse
from users.models import User
from crm.models import Client, Deal


class DashboardTests(TestCase):

    def setUp(self):
        """
        Этот метод запускается ПЕРЕД каждым тестом.
        Здесь мы подготавливаем почву: создаем юзера и клиента.
        """
        # 1. Создаем тестового менеджера
        self.user = User.objects.create_user(
            username='test_manager',
            password='password123',
            role='MANAGER'
        )

        # 2. Создаем клиента (он нужен, чтобы привязать сделку)
        self.client_obj = Client.objects.create(
            company_name='Test Company',
            contact_person='John Doe',
            email='test@example.com',
            phone='123456789',
            manager=self.user
        )

        # 3. Логинимся в систему (виртуальный браузер)
        self.client.force_login(self.user)

    def test_active_deals_counter_increases(self):
        """
        Тест: Проверяем, что при создании сделки счетчик на дашборде растет.
        """

        # Шаг 1: Заходим на Дашборд ДО создания сделки
        url = reverse('crm:dashboard')  # Получаем ссылку /dashboard/
        response = self.client.get(url)  # Делаем GET запрос

        # Проверяем, что страница открылась успешно (код 200)
        self.assertEqual(response.status_code, 200)

        # Проверяем, что в контексте (переменных шаблона) счетчик равен 0
        # 'active_deals_count' - это имя переменной из views.py
        self.assertEqual(response.context['active_deals_count'], 0)
        print("✅ Шаг 1: Сделок нет, счетчик = 0")

        # Шаг 2: Создаем Сделку со статусом 'NEW' (Новая)
        Deal.objects.create(
            title="Тестовая сделка",
            client=self.client_obj,
            manager=self.user,
            amount=50000,
            stage='NEW'  # Важно! Она должна быть активной
        )
        print("⚡ Шаг 2: Сделка создана")

        # Шаг 3: Снова заходим на Дашборд
        response = self.client.get(url)

        # Шаг 4: Проверяем, что счетчик стал равен 1
        self.assertEqual(response.context['active_deals_count'], 1)
        print("✅ Шаг 3: Проверка пройдена, счетчик = 1")

    def test_inactive_deals_dont_count(self):
        """
        Доп. тест: Проверяем, что закрытые сделки (WON/LOST) НЕ увеличивают счетчик активных.
        """
        # Создаем сделку со статусом WON (Успех)
        Deal.objects.create(
            title="Закрытая сделка",
            client=self.client_obj,
            manager=self.user,
            amount=10000,
            stage='WON'
        )

        url = reverse('crm:dashboard')
        response = self.client.get(url)

        # Счетчик должен остаться 0, так как сделка не активна
        self.assertEqual(response.context['active_deals_count'], 0)
        print("✅ Доп. тест: Закрытая сделка не попала в активные")