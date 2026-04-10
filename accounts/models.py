from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "客戶"
        MANAGER = "manager", "管理人員"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    organization = models.CharField(max_length=255, blank=True)

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER or self.is_staff
