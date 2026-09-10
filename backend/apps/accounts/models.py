from django.contrib.auth.models import User
from django.db import models


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
