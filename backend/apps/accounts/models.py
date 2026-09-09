from django.contrib.auth.models import User
from django.db import models


class WeatherData(models.Model):
    record_date = models.DateField(verbose_name="日期", null=True, blank=True)
    max_temperature = models.IntegerField(verbose_name="最高温度", null=True, blank=True)
    min_temperature = models.IntegerField(verbose_name="最低温度", null=True, blank=True)
    weather = models.CharField(verbose_name="天气", max_length=64, null=True, blank=True)
    wind_direction = models.CharField(verbose_name="风向", max_length=32, null=True, blank=True)
    city = models.CharField(verbose_name="城市", max_length=64, null=True, blank=True)
    weekday = models.CharField(verbose_name="周几", max_length=16, null=True, blank=True)
    aqi = models.IntegerField(verbose_name="AQI", null=True, blank=True)
    aqi_level = models.CharField(verbose_name="AQI等级", max_length=32, null=True, blank=True)
    wind_power = models.CharField(verbose_name="风力", max_length=32, null=True, blank=True)

    class Meta:
        db_table = "weather_data"
        managed = False
        verbose_name = "天气数据"
        verbose_name_plural = "天气数据"


class AirQualityData(models.Model):
    record_date = models.DateField(verbose_name="日期", null=True, blank=True)
    quality_level = models.CharField(verbose_name="质量等级", max_length=32, null=True, blank=True)
    aqi_index = models.IntegerField(verbose_name="AQI指数", null=True, blank=True)
    aqi_rank = models.IntegerField(verbose_name="AQI排名", null=True, blank=True)
    pm25 = models.DecimalField(verbose_name="PM2.5", max_digits=10, decimal_places=2, null=True, blank=True)
    pm10 = models.DecimalField(verbose_name="PM10", max_digits=10, decimal_places=2, null=True, blank=True)
    so2 = models.DecimalField(verbose_name="SO2", max_digits=10, decimal_places=2, null=True, blank=True)
    no2 = models.DecimalField(verbose_name="NO2", max_digits=10, decimal_places=2, null=True, blank=True)
    co = models.DecimalField(verbose_name="CO", max_digits=10, decimal_places=2, null=True, blank=True)
    o3 = models.DecimalField(verbose_name="O3", max_digits=10, decimal_places=2, null=True, blank=True)
    city = models.CharField(verbose_name="城市", max_length=64, null=True, blank=True)

    class Meta:
        db_table = "pm25_data"
        managed = False
        verbose_name = "空气质量数据"
        verbose_name_plural = "空气质量数据"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="用户")
    display_name = models.CharField(verbose_name="显示名称", max_length=64, blank=True, default="")
    phone = models.CharField(verbose_name="手机号", max_length=32, blank=True, default="")
    bio = models.CharField(verbose_name="个人简介", max_length=255, blank=True, default="")
    avatar = models.ImageField(verbose_name="头像", upload_to="avatars/", blank=True, null=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    class Meta:
        db_table = "user_profile"
        verbose_name = "用户资料"
        verbose_name_plural = "用户资料"


class EnvironmentObservation(models.Model):
    """A normalized, provider-attributed observation collected by this project."""
    city = models.CharField(max_length=128)
    observed_at = models.DateTimeField()
    collected_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=64)
    source_url = models.URLField(blank=True)
    aqi = models.IntegerField(null=True, blank=True)
    quality = models.CharField(max_length=64, blank=True)
    provider_aqi_category = models.IntegerField(null=True, blank=True)
    pm25 = models.FloatField(null=True, blank=True); pm10 = models.FloatField(null=True, blank=True)
    so2 = models.FloatField(null=True, blank=True); no2 = models.FloatField(null=True, blank=True)
    co = models.FloatField(null=True, blank=True); o3 = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True); humidity = models.FloatField(null=True, blank=True)
    wind_speed = models.FloatField(null=True, blank=True); weather = models.CharField(max_length=128, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True); longitude = models.FloatField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["city", "observed_at"], name="unique_environment_observation")]
        indexes = [models.Index(fields=["city", "-observed_at"])]
