"""
Тесты CRM: дашборд и контроль доступа (regression-тесты к AUDIT.md).

Запуск: python manage.py test --settings=crm_project.settings.test
"""
import json
from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import Client, Deal, Task
from users.models import User

PASSWORD = 'Str0ng-pass-for-tests'


def make_user(username, role='MANAGER'):
    return User.objects.create_user(username=username, password=PASSWORD, role=role)


def make_client(manager, name='Acme', email=None):
    return Client.objects.create(
        company_name=name,
        contact_person='John Doe',
        email=email or f'{name.lower().replace(" ", "")}@example.com',
        phone='123456789',
        manager=manager,
    )


def make_deal(manager, client, title='Сделка', stage='NEW', amount=1000):
    return Deal.objects.create(title=title, client=client, manager=manager, amount=amount, stage=stage)


def make_task(deal, assignee, title='Позвонить'):
    return Task.objects.create(
        deal=deal, assignee=assignee, title=title, description='-', due_date=timezone.now() + timedelta(days=1)
    )


class DashboardTests(TestCase):
    def setUp(self):
        self.user = make_user('test_manager')
        self.client_obj = make_client(self.user, 'Test Company', 'test@example.com')
        self.client.force_login(self.user)

    def test_active_deals_counter_increases(self):
        """Счётчик активных сделок растёт сразу (кэш сбрасывается сигналом)."""
        url = reverse('crm:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_deals_count'], 0)

        make_deal(self.user, self.client_obj, 'Тестовая сделка', 'NEW', 50000)

        response = self.client.get(url)
        self.assertEqual(response.context['active_deals_count'], 1)

    def test_inactive_deals_dont_count(self):
        """Закрытые сделки (WON/LOST) не попадают в активные."""
        make_deal(self.user, self.client_obj, 'Закрытая сделка', 'WON', 10000)
        response = self.client.get(reverse('crm:dashboard'))
        self.assertEqual(response.context['active_deals_count'], 0)

    def test_chart_titles_are_not_injected_into_script(self):
        """Название сделки с </script> не выполняется: данные идут через json_script."""
        payload = '</script><script>alert(1)</script>'
        make_deal(self.user, self.client_obj, payload)
        html = self.client.get(reverse('crm:dashboard')).content.decode()
        self.assertNotIn(payload, html)
        self.assertIn('id="chart-titles"', html)


class AccessControlTests(TestCase):
    """Менеджер не видит и не меняет чужие данные (IDOR)."""

    def setUp(self):
        self.alice = make_user('alice')
        self.bob = make_user('bob')
        self.admin = make_user('boss', role='ADMIN')

        self.bob_client = make_client(self.bob, 'Bob Corp')
        self.bob_deal = make_deal(self.bob, self.bob_client, 'Секретная сделка Боба')
        self.bob_task = make_task(self.bob_deal, self.bob, 'Задача Боба')

        self.alice_client = make_client(self.alice, 'Alice Ltd')
        self.alice_deal = make_deal(self.alice, self.alice_client, 'Сделка Алисы')

        self.client.force_login(self.alice)

    def test_foreign_deal_client_task_pages_return_404(self):
        urls = [
            reverse('crm:deal_detail', args=[self.bob_deal.pk]),
            reverse('crm:deal_update', args=[self.bob_deal.pk]),
            reverse('crm:client_detail', args=[self.bob_client.pk]),
            reverse('crm:client_update', args=[self.bob_client.pk]),
            reverse('crm:task_update', args=[self.bob_task.pk]),
            reverse('crm:task_delete', args=[self.bob_task.pk]),
            reverse('crm:task_create', args=[self.bob_deal.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_cannot_edit_or_delete_foreign_task(self):
        """Чужую задачу нельзя ни изменить, ни удалить."""
        r = self.client.post(reverse('crm:task_update', args=[self.bob_task.pk]), {
            'title': 'hacked', 'description': 'x', 'due_date': '2030-01-01 10:00', 'status': 'COMPLETED',
        })
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.client.post(reverse('crm:task_delete', args=[self.bob_task.pk])).status_code, 404)
        self.bob_task.refresh_from_db()
        self.assertEqual(self.bob_task.title, 'Задача Боба')

    def test_cannot_add_task_to_foreign_deal(self):
        r = self.client.post(reverse('crm:task_create', args=[self.bob_deal.pk]), {
            'title': 'spam', 'description': 'x', 'due_date': '2030-01-01 10:00', 'status': 'PENDING',
        })
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Task.objects.filter(title='spam').exists())

    def test_can_manage_own_task(self):
        r = self.client.post(reverse('crm:task_create', args=[self.alice_deal.pk]), {
            'title': 'Моя задача', 'description': 'x', 'due_date': '2030-01-01 10:00', 'status': 'PENDING',
        })
        self.assertEqual(r.status_code, 302)
        task = Task.objects.get(title='Моя задача')
        self.assertEqual(task.assignee, self.alice)
        self.assertEqual(self.client.get(reverse('crm:task_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('crm:task_delete', args=[task.pk])).status_code, 200)
        self.assertEqual(self.client.post(reverse('crm:task_delete', args=[task.pk])).status_code, 302)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_deal_form_rejects_foreign_client(self):
        """Нельзя привязать свою сделку к чужому клиенту."""
        r = self.client.post(reverse('crm:deal_create'), {
            'client': self.bob_client.pk, 'title': 'Кража клиента', 'amount': '10', 'stage': 'NEW',
        })
        self.assertEqual(r.status_code, 200)  # форма с ошибкой
        self.assertIn('client', r.context['form'].errors)
        self.assertFalse(Deal.objects.filter(title='Кража клиента').exists())

    def test_global_search_is_scoped(self):
        r = self.client.get(reverse('crm:global_search'), {'q': 'Боба'})
        self.assertEqual(r.json()['results'], [])
        r = self.client.get(reverse('crm:global_search'), {'q': 'Bob'})
        self.assertEqual(r.json()['results'], [])
        r = self.client.get(reverse('crm:global_search'), {'q': 'Алисы'})
        self.assertEqual(len(r.json()['results']), 1)

    def test_calendar_events_require_login(self):
        self.client.logout()
        r = self.client.get(reverse('crm:calendar_events'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r['Location'])

    def test_calendar_events_only_own(self):
        titles = [e['title'] for e in self.client.get(reverse('crm:calendar_events')).json()]
        self.assertTrue(any('Сделка Алисы' in t for t in titles))
        self.assertFalse(any('Боба' in t for t in titles))

    def test_manager_cannot_delete_deal_or_client(self):
        """Удаление — только админ; менеджеру 404 (не раскрываем раздел)."""
        self.assertEqual(self.client.get(reverse('crm:deal_delete', args=[self.alice_deal.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('crm:deal_delete', args=[self.alice_deal.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('crm:client_delete', args=[self.alice_client.pk])).status_code, 404)
        self.assertTrue(Deal.objects.filter(pk=self.alice_deal.pk).exists())

    def test_admin_can_delete_deal(self):
        """Администратор удаляет сделку через POST со страницы подтверждения."""
        self.client.force_login(self.admin)
        r = self.client.post(reverse('crm:deal_delete', args=[self.bob_deal.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Deal.objects.filter(pk=self.bob_deal.pk).exists())

    def test_admin_sees_everything(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('crm:deal_detail', args=[self.bob_deal.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('crm:client_detail', args=[self.alice_client.pk])).status_code, 200)

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()
        for name in ['crm:deal_list', 'crm:client_list', 'crm:dashboard', 'crm:task_list', 'crm:global_search']:
            with self.subTest(name=name):
                r = self.client.get(reverse(name))
                self.assertEqual(r.status_code, 302)
                self.assertIn(reverse('login'), r['Location'])


class CongratsEmailTests(TestCase):
    def setUp(self):
        self.user = make_user('seller')
        self.client_obj = make_client(self.user, 'Buyer', 'buyer@example.com')
        self.deal = make_deal(self.user, self.client_obj, 'Большая сделка', 'IN_PROGRESS')
        self.client.force_login(self.user)

    def _save(self, stage):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('crm:deal_update', args=[self.deal.pk]), {
                'client': self.client_obj.pk, 'title': self.deal.title, 'amount': '1000', 'stage': stage,
            })

    def test_email_sent_once_on_transition_to_won(self):
        self.assertEqual(self._save('WON').status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        # Повторное сохранение уже выигранной сделки письмо не дублирует.
        self._save('WON')
        self.assertEqual(len(mail.outbox), 1)


class ApiAccessTests(TestCase):
    def setUp(self):
        self.alice = make_user('alice')
        self.bob = make_user('bob')
        self.bob_client = make_client(self.bob, 'Bob Corp')
        self.bob_deal = make_deal(self.bob, self.bob_client, 'Bob deal')
        self.api = APIClient()
        self.api.force_authenticate(self.alice)

    def test_create_client_sets_manager(self):
        """Клиент, созданный через API, получает текущего пользователя в manager."""
        r = self.api.post('/api/v1/clients/', {
            'company_name': 'New', 'contact_person': 'X', 'email': 'new@example.com', 'phone': '1',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Client.objects.get(email='new@example.com').manager, self.alice)

    def test_foreign_objects_are_invisible(self):
        self.assertEqual(self.api.get(f'/api/v1/clients/{self.bob_client.pk}/').status_code, 404)
        self.assertEqual(self.api.get(f'/api/v1/deals/{self.bob_deal.pk}/').status_code, 404)
        self.assertEqual(self.api.get('/api/v1/deals/').json()['count'], 0)

    def test_cannot_link_deal_to_foreign_client(self):
        r = self.api.post('/api/v1/deals/', {
            'title': 'x', 'amount': '1', 'stage': 'NEW', 'client': self.bob_client.pk,
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('client', r.json())

    def test_cannot_create_task_in_foreign_deal(self):
        r = self.api.post('/api/v1/tasks/', {
            'title': 'x', 'description': 'x', 'due_date': '2030-01-01T10:00:00Z', 'deal': self.bob_deal.pk,
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('deal', r.json())

    def test_manager_cannot_delete_own_deal_via_api(self):
        own_client = make_client(self.alice, 'Mine')
        own_deal = make_deal(self.alice, own_client, 'Mine')
        self.assertEqual(self.api.delete(f'/api/v1/deals/{own_deal.pk}/').status_code, 403)
        self.assertTrue(Deal.objects.filter(pk=own_deal.pk).exists())

    def test_anonymous_api_denied(self):
        anon = APIClient()
        self.assertIn(anon.get('/api/v1/deals/').status_code, (401, 403))

    def test_basic_auth_disabled(self):
        """BasicAuthentication убрана: пароль в каждом запросе API не принимается."""
        import base64
        anon = APIClient()
        token = base64.b64encode(f'alice:{PASSWORD}'.encode()).decode()
        anon.credentials(HTTP_AUTHORIZATION=f'Basic {token}')
        self.assertIn(anon.get('/api/v1/deals/').status_code, (401, 403))

    def test_swagger_hidden_from_non_staff(self):
        self.client.force_login(self.alice)
        url = reverse('schema-json', kwargs={'format': '.json'})
        self.assertIn(self.client.get(url).status_code, (401, 403))
        self.assertIn(self.client.get(reverse('schema-swagger-ui')).status_code, (401, 403))


class SearchResponseTests(TestCase):
    def test_search_returns_raw_text_for_client_side_escaping(self):
        """API поиска отдаёт данные как есть; экранирует их base.html (escapeHtml)."""
        user = make_user('eve')
        make_client(user, '<img src=x onerror=alert(1)>', 'x@example.com')
        self.client.force_login(user)
        data = self.client.get(reverse('crm:global_search'), {'q': 'img'}).json()
        self.assertEqual(data['results'][0]['title'], '<img src=x onerror=alert(1)>')
        base = self.client.get(reverse('crm:deal_list')).content.decode()
        self.assertIn('escapeHtml(item.title)', base)
        json.dumps(data)  # ответ сериализуем
