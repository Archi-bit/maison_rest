from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.staff.models import EmployeeProfile


class EmployeeProfileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="waiter")

    def test_profile_is_linked_to_the_user(self):
        profile = EmployeeProfile.objects.create(
            user=self.user, role=EmployeeProfile.Role.WAITER
        )

        self.assertEqual(profile.user, self.user)
        self.assertEqual(self.user.employee_profile, profile)
        self.assertEqual(str(profile), "waiter — Официант")

    def test_user_cannot_have_two_profiles(self):
        EmployeeProfile.objects.create(
            user=self.user, role=EmployeeProfile.Role.WAITER
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            EmployeeProfile.objects.create(
                user=self.user, role=EmployeeProfile.Role.ADMIN
            )

    def test_deleting_user_removes_profile(self):
        profile = EmployeeProfile.objects.create(
            user=self.user, role=EmployeeProfile.Role.WAITER
        )

        self.user.delete()

        self.assertFalse(
            EmployeeProfile.objects.filter(pk=profile.pk).exists()
        )
