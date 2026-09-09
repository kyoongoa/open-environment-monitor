from django.contrib import admin

from .models import AirQualityData, UserProfile, WeatherData


admin.site.site_header = "环境监测数据分析系统"
admin.site.site_title = "环境监测超管后台"
admin.site.index_title = "后台管理"


@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = (
        "record_date",
        "city",
        "weather",
        "max_temperature",
        "min_temperature",
        "aqi",
        "aqi_level",
    )
    list_filter = ("city", "weather", "aqi_level")
    search_fields = ("city", "weather", "aqi_level")
    ordering = ("-record_date",)


@admin.register(AirQualityData)
class AirQualityDataAdmin(admin.ModelAdmin):
    list_display = (
        "record_date",
        "city",
        "quality_level",
        "aqi_index",
        "aqi_rank",
        "pm25",
        "pm10",
    )
    list_filter = ("city", "quality_level")
    search_fields = ("city", "quality_level")
    ordering = ("-record_date",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "phone", "updated_at")
    search_fields = ("user__username", "display_name", "phone")
    ordering = ("-updated_at",)
