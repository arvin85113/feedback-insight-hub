from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Platform Settings", {"fields": ("role", "organization", "notification_opt_in")}),
    )
    list_display = ("username", "email", "role", "organization", "notification_opt_in", "is_staff")
