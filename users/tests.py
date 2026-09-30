from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import User


class LoginBruteForceTests(TestCase):
    def setUp(self):
        User.objects.create_user(username='victim', password='Correct-horse-42')

    @override_settings(AXES_FAILURE_LIMIT=3)
    def test_lockout_after_failures(self):
        url = reverse('login')
        for _ in range(3):
            self.client.post(url, {'username': 'victim', 'password': 'wrong'}, REMOTE_ADDR='10.0.0.1')
        # Даже верный пароль после блокировки не пускает.
        r = self.client.post(url, {'username': 'victim', 'password': 'Correct-horse-42'}, REMOTE_ADDR='10.0.0.1')
        self.assertEqual(r.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_new_users_are_managers_not_admins(self):
        self.assertEqual(User.objects.get(username='victim').role, User.Role.MANAGER)
