from django.contrib import admin

from .models import EnvironmentObservation, UserProfile


@admin.register(EnvironmentObservation)
class EnvironmentObservationAdmin(admin.ModelAdmin):
    list_display = ("city", "observed_at", "source", "aqi", "pm25", "temperature")
    list_filter = ("source", "quality")
    search_fields = ("city",)
    ordering = ("-observed_at",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "updated_at")
