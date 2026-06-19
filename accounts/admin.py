from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "role", "created_at"]
    list_filter = ["plan", "role"]
    search_fields = ["user__username", "user__email"]
