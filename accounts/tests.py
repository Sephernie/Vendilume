from io import StringIO

from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command

from .roles import (
    ADMINISTRATORS,
    MANAGERS,
    ROLE_PERMISSIONS,
    SALES_ANALYSTS,
)


class AuthenticationViewTests(TestCase):
    def setUp(self):
        self.password = "SecureTestPassword123!"
        self.user = get_user_model().objects.create_user(
            username="test.employee",
            password=self.password,
        )
        view_dataset_permission = Permission.objects.get(
            content_type__app_label="datasets",
            codename="view_dataset",
        )
        self.user.user_permissions.add(
            view_dataset_permission,
        )

    def test_login_page_loads_successfully(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertContains(response, "Sign in")
        self.assertContains(response, "Turn today’s data")
        self.assertNotContains(response, "topbar-signin")
        self.assertNotContains(response, "Analytics ready")

    def test_valid_login_redirects_to_dataset_history(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.user.username,
                "password": self.password,
            },
        )

        self.assertRedirects(
            response,
            reverse("datasets:history"),
        )
        self.assertIn(SESSION_KEY, self.client.session)

    def test_authenticated_user_can_change_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": self.password,
                "new_password1": "UpdatedPassword456!",
                "new_password2": "UpdatedPassword456!",
            },
        )

        self.assertRedirects(
            response,
            reverse("password_change_done"),
        )

        self.user.refresh_from_db()
        self.assertTrue(
            self.user.check_password("UpdatedPassword456!")
        )

    def test_logout_ends_authenticated_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)

class RoleSetupCommandTests(TestCase):
    def test_setup_roles_creates_expected_permissions(self):
        output = StringIO()

        call_command("setup_roles", stdout=output)

        for role_name, expected_permissions in (
            ROLE_PERMISSIONS.items()
        ):
            group = Group.objects.get(name=role_name)

            actual_permissions = set(
                group.permissions.values_list(
                    "content_type__app_label",
                    "codename",
                )
            )

            self.assertEqual(
                actual_permissions,
                set(expected_permissions),
            )

        self.assertIn(ADMINISTRATORS, output.getvalue())
        self.assertIn(SALES_ANALYSTS, output.getvalue())
        self.assertIn(MANAGERS, output.getvalue())

    def test_setup_roles_is_idempotent(self):
        call_command("setup_roles")
        call_command("setup_roles")

        self.assertEqual(Group.objects.count(), 3)
class AdministratorAccountManagementTests(TestCase):
    def setUp(self):
        call_command(
            "setup_roles",
            stdout=StringIO(),
        )

        user_model = get_user_model()

        self.administrator = user_model.objects.create_user(
            username="staff.administrator",
            password="TestPassword123!",
            is_staff=True,
        )
        self.administrator.groups.add(
            Group.objects.get(name=ADMINISTRATORS)
        )

        self.manager = user_model.objects.create_user(
            username="ordinary.manager",
            password="TestPassword123!",
        )
        self.manager.groups.add(
            Group.objects.get(name=MANAGERS)
        )

    def test_staff_administrator_can_manage_users(self):
        self.client.force_login(self.administrator)

        protected_admin_urls = [
            reverse("admin:index"),
            reverse("admin:auth_user_changelist"),
            reverse("admin:auth_user_add"),
        ]

        for url in protected_admin_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_manager_cannot_access_user_management(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("admin:auth_user_changelist")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("admin:login"),
            response.url,
        )

    def test_public_signup_is_not_available(self):
        response = self.client.get("/accounts/signup/")

        self.assertEqual(response.status_code, 404)
