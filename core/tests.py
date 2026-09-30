import importlib
import os
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase
from django.urls import reverse


class HealthAndHeadersTests(TestCase):
    def test_healthz_ok(self):
        r = self.client.get('/healthz/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {'status': 'ok'})

    def test_security_headers(self):
        r = self.client.get(reverse('login'))
        self.assertEqual(r.status_code, 200)
        self.assertIn("frame-ancestors 'none'", r['Content-Security-Policy'])
        self.assertIn("object-src 'none'", r['Content-Security-Policy'])
        self.assertIn('camera=()', r['Permissions-Policy'])
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_eval_allowed_only_on_lab_page(self):
        from users.models import User
        self.client.force_login(User.objects.create_user('u1', password='Str0ng-pass-for-tests'))
        self.assertIn("'unsafe-eval'", self.client.get(reverse('crm:lab'))['Content-Security-Policy'])
        self.assertNotIn("'unsafe-eval'", self.client.get(reverse('crm:dashboard'))['Content-Security-Policy'])

    def test_inline_scripts_carry_request_nonce(self):
        """script-src без 'unsafe-inline': встроенные скрипты работают только с nonce этого запроса."""
        import re
        from users.models import User
        self.client.force_login(User.objects.create_user('u2', password='Str0ng-pass-for-tests'))
        r1 = self.client.get(reverse('crm:dashboard'))
        csp = r1['Content-Security-Policy']
        script_src = next(d for d in csp.split('; ') if d.startswith('script-src '))
        self.assertNotIn("'unsafe-inline'", script_src)
        self.assertIn("script-src-attr 'none'", csp)
        nonce = re.search(r"'nonce-([^']+)'", script_src).group(1)
        html = r1.content.decode()
        inline = re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*application/json)([^>]*)>', html)
        self.assertTrue(inline)
        self.assertTrue(all(f'nonce="{nonce}"' in attrs for attrs in inline), inline)
        self.assertNotRegex(html, r'\son(click|submit|load|change)=')
        # nonce одноразовый: у следующего запроса другой
        r2 = self.client.get(reverse('crm:dashboard'))
        self.assertNotIn(nonce, r2['Content-Security-Policy'])

    def test_admin_honeypot_on_admin_url(self):
        r = self.client.get('/admin/', follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('/admin/login/', r.redirect_chain[-1][0])


class ProdSettingsTests(SimpleTestCase):
    """prod-настройки не стартуют со слабым ключом или без ALLOWED_HOSTS."""

    def _load(self, env):
        with mock.patch.dict(os.environ, env, clear=False):
            import crm_project.settings.base as base
            importlib.reload(base)
            import crm_project.settings.prod as prod
            return importlib.reload(prod)

    def tearDown(self):
        import crm_project.settings.base as base
        importlib.reload(base)

    def test_placeholder_secret_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self._load({'SECRET_KEY': 'your_secret_key_here', 'ALLOWED_HOSTS': 'crm.example.com'})

    def test_wildcard_hosts_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self._load({'SECRET_KEY': 'k' * 60, 'ALLOWED_HOSTS': '*'})

    def test_valid_config_loads(self):
        prod = self._load({'SECRET_KEY': 'k' * 60, 'ALLOWED_HOSTS': 'crm.example.com'})
        self.assertFalse(prod.DEBUG)
        self.assertTrue(prod.SESSION_COOKIE_SECURE)
        self.assertEqual(prod.ALLOWED_HOSTS, ['crm.example.com'])
