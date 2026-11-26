from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.catalog.models import Dish
from apps.staff.models import EmployeeProfile


class StaffAPITest(APITestCase):
    password = "test-password-for-staff"

    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.employee = users.create_user(
            username="waiter",
            first_name="Айбек",
            last_name="Асанов",
            email="waiter@example.com",
            password=cls.password,
        )
        cls.profile = EmployeeProfile.objects.create(
            user=cls.employee, role=EmployeeProfile.Role.WAITER
        )
        cls.other_employee = users.create_user(
            username="owner", password=cls.password
        )
        cls.other_profile = EmployeeProfile.objects.create(
            user=cls.other_employee, role=EmployeeProfile.Role.OWNER
        )
        cls.visitor = users.create_user(
            username="visitor", password=cls.password
        )
        cls.admin_user = users.create_user(
            username="django_admin", password=cls.password, is_staff=True
        )

    def login(self, username="waiter", password=None):
        return self.client.post(
            reverse("staff:login"),
            {
                "username": username,
                "password": self.password if password is None else password,
            },
            format="json",
        )

    def refresh(self, refresh_token):
        return self.client.post(
            reverse("staff:token-refresh"),
            {"refresh": refresh_token},
            format="json",
        )

    def get_profile(self, access_token):
        return self.client.get(
            reverse("staff:me"), HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

    def test_employee_gets_token_pair_and_can_refresh_access(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"access", "refresh"})
        self.assertIn("no-store", response["Cache-Control"])
        refresh_response = self.refresh(response.json()["refresh"])
        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(set(refresh_response.json()), {"access"})
        self.assertIn("no-store", refresh_response["Cache-Control"])
        access = refresh_response.json()["access"]
        self.assertNotEqual(access, response.json()["access"])
        self.assertEqual(self.get_profile(access).status_code, 200)

    def test_login_failures_return_the_same_error(self):
        self.other_employee.is_active = False
        self.other_employee.save(update_fields=["is_active"])
        wrong_password = self.login(password="wrong")
        self.assertEqual(wrong_password.status_code, 401)

        for username in ("unknown", "owner", "visitor", "django_admin"):
            with self.subTest(username=username):
                response = self.login(username)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), wrong_password.json())

    def test_missing_credentials_return_validation_error(self):
        response = self.client.post(
            reverse("staff:login"), {"username": "waiter"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"password"})

    def test_login_preserves_spaces_in_password(self):
        password = f" {self.password} "
        self.employee.set_password(password)
        self.employee.save(update_fields=["password"])

        self.assertEqual(self.login(password=password).status_code, 200)
        self.assertEqual(self.login(password=self.password).status_code, 401)

    def test_refresh_rejects_invalid_expired_and_access_tokens(self):
        refresh = RefreshToken.for_user(self.employee)
        access = str(refresh.access_token)
        refresh.set_exp(lifetime=timedelta(seconds=-1))

        for case, token in (
            ("invalid", "invalid"),
            ("expired", str(refresh)),
            ("access", access),
        ):
            with self.subTest(case=case):
                response = self.refresh(token)
                self.assertEqual(response.status_code, 401)
                self.assertNotIn("access", response.json())

    def test_me_only_returns_the_current_employees_public_fields(self):
        access = self.login().json()["access"]
        response = self.client.get(
            reverse("staff:me"),
            {"id": self.other_profile.pk},
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": self.profile.pk,
                "first_name": "Айбек",
                "last_name": "Асанов",
                "username": "waiter",
                "role": "waiter",
            },
        )
        self.assertIn("no-store", response["Cache-Control"])

    def test_me_requires_an_access_token_even_with_a_session(self):
        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(reverse("staff:me")).status_code, 401)
        for token in ("invalid", self.login().json()["refresh"]):
            self.assertEqual(self.get_profile(token).status_code, 401)

    def test_visitor_tokens_do_not_grant_staff_access(self):
        refresh = RefreshToken.for_user(self.visitor)
        response = self.get_profile(str(refresh.access_token))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.refresh(str(refresh)).status_code, 401)

    def test_deactivated_employee_loses_access_and_cannot_refresh(self):
        tokens = self.login().json()
        self.employee.is_active = False
        self.employee.save(update_fields=["is_active"])

        self.assertEqual(self.get_profile(tokens["access"]).status_code, 401)
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

    def test_employee_without_profile_loses_access_and_cannot_refresh(self):
        tokens = self.login().json()
        self.profile.delete()

        self.assertEqual(self.get_profile(tokens["access"]).status_code, 403)
        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

    def test_deleted_employee_cannot_refresh(self):
        tokens = self.login().json()
        self.employee.delete()

        self.assertEqual(self.refresh(tokens["refresh"]).status_code, 401)

    def test_admin_without_permissions_cannot_add_employee_profile(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("admin:staff_employeeprofile_add"))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_add_employee_profile_in_admin(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin"
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            reverse("admin:staff_employeeprofile_add"),
            {"user": self.visitor.pk, "role": EmployeeProfile.Role.ADMIN},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            self.visitor.employee_profile.role, EmployeeProfile.Role.ADMIN
        )
        self.assertEqual(self.login("visitor").status_code, 200)

    def test_guest_can_add_catalog_dish_to_cart_without_jwt(self):
        dish = Dish.objects.create(name="Суп", price="125.00")
        cart = self.client.post(reverse("guest-cart"))
        self.assertEqual(cart.status_code, 201)

        item = self.client.post(
            reverse("cart-items"),
            {"dish_id": dish.pk, "quantity": 2},
            format="json",
            HTTP_X_CART_TOKEN=cart["X-Cart-Token"],
        )

        self.assertEqual(item.status_code, 201)
        response = self.client.get(
            reverse("guest-cart"), HTTP_X_CART_TOKEN=cart["X-Cart-Token"]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"total_quantity": 2, "total_price": "250.00"}
        )
