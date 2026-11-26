from django.contrib import admin

from apps.staff.models import EmployeeProfile


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_select_related = ("user",)
    search_fields = ("user__username", "user__first_name", "user__last_name")
    list_filter = ("role",)
    autocomplete_fields = ("user",)
