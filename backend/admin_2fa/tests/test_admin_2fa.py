"""Admin 2FA: generic tests, portable as-is (no project-specific model or URL).

Ported from the pytest version of the fleet reference (Poker_server) to
django.test.TestCase, the runner of this project (`manage.py test`).
The project's own "public API unchanged" test lives next to its API tests.
"""
import re
import time
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.checks import run_checks
from django.core.management import CommandError, call_command
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from admin_2fa.utils import BACKUP_CODE_COUNT, Redacted

PASSWORD = "Adm1n-Passw0rd!"
INDEX = "/admin/"


def _make_user(login, staff=True, superuser=False):
    user_model = get_user_model()
    user = user_model._default_manager.create_user(
        **{user_model.USERNAME_FIELD: login}, password=PASSWORD
    )
    user.is_staff = staff
    user.is_superuser = superuser
    user.save()
    return user


def _login_value(user):
    return getattr(user, get_user_model().USERNAME_FIELD)


def _password_login(client, user, next_url=INDEX):
    return client.post(
        reverse("admin:login"),
        {"username": _login_value(user), "password": PASSWORD, "next": next_url},
    )


def _code(device, offset=0):
    totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
    totp.time = time.time() + offset * device.step
    return f"{totp.token():0{device.digits}d}"


def _enrolled_device(user):
    return TOTPDevice.objects.create(user=user, name="admin-2fa", confirmed=True)


def _backup_codes(user, codes=("aaaa2222", "bbbb3333")):
    device = StaticDevice.objects.create(user=user, name="admin-2fa-backup", confirmed=True)
    for code in codes:
        StaticToken.objects.create(device=device, token=code)
    return device


class RedactedTests(SimpleTestCase):
    def test_redacted_hides_the_value_from_tracebacks(self):
        secret = Redacted(["code1", "code2"])
        self.assertEqual(repr(secret), "<redacted>")
        self.assertEqual(list(secret), ["code1", "code2"])
        self.assertEqual(str(Redacted("ABCD")), "ABCD")
        self.assertEqual(Redacted("<b>").__html__(), "&lt;b&gt;")


class Admin2FATests(TestCase):
    def setUp(self):
        self.staff = _make_user("staff@example.com", superuser=True)

    # --- wiring -----------------------------------------------------------------

    def test_system_checks_pass_with_the_settings_of_this_project(self):
        self.assertEqual([e for e in run_checks() if e.id.startswith("admin_2fa.")], [])

    def test_system_checks_catch_a_half_done_port(self):
        from django.conf import settings

        from admin_2fa.checks import check_admin_2fa

        middleware = [m for m in settings.MIDDLEWARE if "django_otp" not in m]
        with self.settings(MIDDLEWARE=middleware, OTP_TOTP_THROTTLE_FACTOR=0):
            self.assertEqual({e.id for e in check_admin_2fa(None)}, {"admin_2fa.E002", "admin_2fa.E004"})

    # --- enrolment (first admin login) -------------------------------------------

    def test_staff_without_device_is_sent_to_enrolment_and_never_reaches_the_admin(self):
        response = _password_login(self.client, self.staff)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("admin:2fa_setup")))

        index = self.client.get(INDEX)
        self.assertEqual(index.status_code, 302)
        self.assertTrue(index.url.startswith(reverse("admin:login")))
        # The login page itself forwards the half-logged-in user to the second factor.
        login_page = self.client.get(index.url)
        self.assertEqual(login_page.status_code, 302)
        self.assertTrue(login_page.url.startswith(reverse("admin:2fa_setup")))
        # Any admin page, not just the index.
        self.assertEqual(self.client.get(reverse("admin:password_change")).status_code, 302)

    def test_enrolment_page_shows_a_qr_code_and_the_key_and_keeps_the_same_secret(self):
        _password_login(self.client, self.staff)
        first = self.client.get(reverse("admin:2fa_setup"))
        self.assertEqual(first.status_code, 200)
        body = first.content.decode()
        self.assertIn('role="img" aria-label="QR code"', body)
        self.assertIsNone(re.search(r"<script(?![^>]*\bsrc=)", body))  # no inline script (CSP)
        self.assertNotIn(" style=", body.split("<!-- END SVGs -->")[0].split("<body")[1])  # no inline style
        device = TOTPDevice.objects.get(user=self.staff)
        self.assertFalse(device.confirmed)
        self.assertIn("no-cache", first["Cache-Control"])
        self.assertIn("no-store", first["Cache-Control"])

        self.client.get(reverse("admin:2fa_setup"))
        self.assertEqual(TOTPDevice.objects.filter(user=self.staff).count(), 1)  # a reload keeps the QR

    def test_enrolment_with_the_right_code_confirms_and_shows_backup_codes_once(self):
        _password_login(self.client, self.staff)
        self.client.get(reverse("admin:2fa_setup"))
        device = TOTPDevice.objects.get(user=self.staff)

        response = self.client.post(reverse("admin:2fa_setup"), {"token": _code(device), "next": INDEX})
        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        tokens = list(StaticToken.objects.filter(device__user=self.staff).values_list("token", flat=True))
        self.assertEqual(len(tokens), BACKUP_CODE_COUNT)
        body = response.content.decode()
        self.assertTrue(all(token in body for token in tokens))
        self.assertIn("no-store", response["Cache-Control"])

        self.assertEqual(self.client.get(INDEX).status_code, 200)
        # Re-posting (a reload) never shows the codes again.
        again = self.client.post(reverse("admin:2fa_setup"), {"token": _code(device), "next": INDEX})
        self.assertEqual(again.status_code, 302)
        self.assertFalse(any(token in self.client.get(INDEX).content.decode() for token in tokens))

    def test_enrolment_with_a_wrong_code_is_refused(self):
        _password_login(self.client, self.staff)
        self.client.get(reverse("admin:2fa_setup"))
        device = TOTPDevice.objects.get(user=self.staff)
        wrong = f"{(int(_code(device)) + 1) % 1_000_000:06d}"

        response = self.client.post(reverse("admin:2fa_setup"), {"token": wrong})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Wrong code", response.content)
        device.refresh_from_db()
        self.assertFalse(device.confirmed)
        self.assertFalse(StaticDevice.objects.filter(user=self.staff).exists())
        self.assertEqual(self.client.get(INDEX).status_code, 302)

    def test_enrolled_user_cannot_re_enrol_without_a_reset(self):
        _enrolled_device(self.staff)
        _password_login(self.client, self.staff)
        response = self.client.get(reverse("admin:2fa_setup"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("admin:2fa_verify")))
        self.assertEqual(TOTPDevice.objects.filter(user=self.staff).count(), 1)

    # --- every later login --------------------------------------------------------

    def test_staff_with_a_device_must_give_the_code(self):
        device = _enrolled_device(self.staff)
        response = _password_login(self.client, self.staff, next_url="/admin/auth/group/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("admin:2fa_verify")))
        self.assertEqual(self.client.get(INDEX).status_code, 302)

        bad = self.client.post(reverse("admin:2fa_verify"), {"token": "000000"})
        self.assertEqual(bad.status_code, 200)
        self.assertEqual(self.client.get(INDEX).status_code, 302)

        device.throttle_reset()  # the wrong code above armed the 1 s delay
        good = self.client.post(
            reverse("admin:2fa_verify"), {"token": _code(device), "next": "/admin/auth/group/"}
        )
        self.assertEqual(good.status_code, 302)
        self.assertEqual(good.url, "/admin/auth/group/")
        self.assertEqual(self.client.get(INDEX).status_code, 200)

    def test_wrong_codes_are_throttled_by_django_otp(self):
        device = _enrolled_device(self.staff)
        _password_login(self.client, self.staff)
        self.client.post(reverse("admin:2fa_verify"), {"token": "000000"})
        device.refresh_from_db()
        self.assertEqual(device.throttling_failure_count, 1)

        # Even the right code is refused while the delay runs.
        response = self.client.post(reverse("admin:2fa_verify"), {"token": _code(device)})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Too many failed attempts", response.content)
        self.assertEqual(self.client.get(INDEX).status_code, 302)

    def test_backup_code_works_exactly_once(self):
        _enrolled_device(self.staff)
        _backup_codes(self.staff)

        _password_login(self.client, self.staff)
        used = self.client.post(reverse("admin:2fa_verify"), {"token": "AAAA 2222"})  # spaces and caps ok
        self.assertEqual(used.status_code, 302)
        self.assertEqual(self.client.get(INDEX).status_code, 200)
        self.assertFalse(StaticToken.objects.filter(token="aaaa2222").exists())

        self.client.logout()
        other = Client()
        _password_login(other, self.staff)
        reused = other.post(reverse("admin:2fa_verify"), {"token": "aaaa2222"})
        self.assertEqual(reused.status_code, 200)
        self.assertIn(b"Invalid code", reused.content)
        self.assertEqual(other.get(INDEX).status_code, 302)

    def test_next_is_never_an_external_url(self):
        device = _enrolled_device(self.staff)
        _password_login(self.client, self.staff)
        response = self.client.post(
            reverse("admin:2fa_verify"), {"token": _code(device), "next": "https://evil.example/"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, INDEX)

    # --- who may reach the 2FA pages ----------------------------------------------

    def test_non_staff_gets_no_admin_access(self):
        user = _make_user("user@example.com", staff=False)
        response = _password_login(self.client, user)
        self.assertEqual(response.status_code, 200)  # the login form again, with its error
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.client.force_login(user)
        for url in (INDEX, reverse("admin:2fa_setup"), reverse("admin:2fa_verify")):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertTrue(response.url.startswith(reverse("admin:login")), url)
        self.assertFalse(TOTPDevice.objects.filter(user=user).exists())

    def test_anonymous_is_sent_to_the_password_login(self):
        for url in (reverse("admin:2fa_setup"), reverse("admin:2fa_verify")):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertTrue(response.url.startswith(reverse("admin:login")), url)

    def test_post_without_csrf_token_is_refused(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        response = csrf_client.post(reverse("admin:2fa_setup"), {"token": "123456"})
        self.assertEqual(response.status_code, 403)

    # --- reset command ------------------------------------------------------------

    def test_reset_command_deletes_the_devices_and_forces_a_new_enrolment(self):
        device = _enrolled_device(self.staff)
        _backup_codes(self.staff)
        _password_login(self.client, self.staff)
        self.client.post(reverse("admin:2fa_verify"), {"token": _code(device)})
        self.assertEqual(self.client.get(INDEX).status_code, 200)

        out = StringIO()
        call_command("admin_2fa_reset", _login_value(self.staff).upper(), stdout=out)
        self.assertIn("Deleted 2 OTP device(s)", out.getvalue())
        self.assertFalse(TOTPDevice.objects.filter(user=self.staff).exists())
        self.assertFalse(StaticDevice.objects.filter(user=self.staff).exists())

        # The session verified with the deleted device is no longer verified.
        response = self.client.get(INDEX)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.get(response.url).url.startswith(reverse("admin:2fa_setup")))

    def test_reset_command_unlock_keeps_the_devices(self):
        device = _enrolled_device(self.staff)
        device.throttle_increment()
        call_command("admin_2fa_reset", _login_value(self.staff), "--unlock", stdout=StringIO())
        device.refresh_from_db()
        self.assertEqual(device.throttling_failure_count, 0)
        self.assertTrue(TOTPDevice.objects.filter(user=self.staff).exists())

    def test_reset_command_unknown_user(self):
        with self.assertRaises(CommandError):
            call_command("admin_2fa_reset", "nobody@example.com", stdout=StringIO())

    def test_force_admin_login_helper_opens_the_admin(self):
        from admin_2fa.testing import force_admin_login

        force_admin_login(self.client, self.staff)
        self.assertEqual(self.client.get(INDEX).status_code, 200)
