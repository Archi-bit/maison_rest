from django.conf import settings
from django.db import models


class EmployeeProfile(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Владелец"
        ADMIN = "admin", "Администратор"
        WAITER = "waiter", "Официант"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    role = models.CharField(max_length=10, choices=Role.choices)

    def __str__(self):
        return f"{self.user.get_username()} — {self.get_role_display()}"
