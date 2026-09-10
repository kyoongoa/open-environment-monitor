from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase, override_settings

from .environment import EnvironmentDataProvider, ProviderError, cache
from .models import EnvironmentObservation


class FakeProvider(EnvironmentDataProvider):
    name = "fake"
    calls = 0
    def fetch_current(self, city):
        type(self).calls += 1
        canonical = {"Beijing": "北京市", "北京市": "北京市", "Lanzhou": "兰州市", "兰州市": "兰州市"}.get(city, city)
        return {"city": canonical, "observed_at": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(), "collected_at": datetime.now(timezone.utc).isoformat(), "source": self.name, "source_url": "https://example.test", "aqi": 42, "quality": "Good", "pm25": 10.0, "pm10": 20.0}


@override_settings(ENVIRONMENT_CACHE_SECONDS=300)
class EnvironmentApiTests(TestCase):
    def setUp(self):
        cache._data.clear()
        FakeProvider.calls = 0

    @patch("apps.accounts.environment._transliterate_chinese", side_effect=lambda city: {"北京": "beijing", "兰州": "lanzhou"}[city])
    @patch("apps.accounts.environment.get_provider", return_value=FakeProvider())
    def test_city_aliases_share_realtime_history_and_trend(self, _provider, _transliterate):
        first = self.client.get("/api/environment/realtime/", {"city": "Beijing"})
        second = self.client.get("/api/environment/realtime/", {"city": "北京"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["data"]["data_status"], "live")
        self.assertEqual(first.json()["data"]["city"], "北京市")
        self.assertEqual(second.json()["data"]["data_status"], "cached")
        self.assertEqual(FakeProvider.calls, 1)
        self.assertEqual(EnvironmentObservation.objects.count(), 1)
        for alias in ("Beijing", "北京", "北京市"):
            history_response = self.client.get("/api/environment/history/", {"city": alias})
            trend_response = self.client.get("/api/environment/trend/", {"city": alias})
            self.assertEqual(history_response.status_code, 200)
            self.assertEqual(history_response.json()["data"][0]["city"], "北京市")
            self.assertEqual(trend_response.status_code, 200)
            self.assertEqual(trend_response.json()["data"][0]["aqi"], 42)

    @patch("apps.accounts.environment._transliterate_chinese", return_value="lanzhou")
    @patch("apps.accounts.environment.get_provider", return_value=FakeProvider())
    def test_lanzhou_aliases_share_canonical_history_and_trend(self, _provider, _transliterate):
        first = self.client.get("/api/environment/realtime/", {"city": "Lanzhou"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["data"]["city"], "兰州市")
        for alias in ("Lanzhou", "兰州", "兰州市"):
            history_response = self.client.get("/api/environment/history/", {"city": alias})
            trend_response = self.client.get("/api/environment/trend/", {"city": alias})
            self.assertEqual(history_response.status_code, 200)
            self.assertEqual(history_response.json()["data"][0]["city"], "兰州市")
            self.assertEqual(trend_response.status_code, 200)

    @override_settings(OPENWEATHER_API_KEY="")
    def test_missing_key_returns_explicit_unavailable_error(self):
        response = self.client.get("/api/environment/realtime/", {"city": "北京"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENWEATHER_API_KEY", response.json()["error"]["message"])

    def test_history_requires_city(self):
        response = self.client.get("/api/environment/history/")
        self.assertEqual(response.status_code, 400)

    def test_dashboard_summary_counts_real_observations_by_available_fields(self):
        now = datetime.now(timezone.utc)
        EnvironmentObservation.objects.create(city="北京市", observed_at=now, source="openweather", temperature=20, humidity=40, pm25=12)
        EnvironmentObservation.objects.create(city="兰州市", observed_at=now.replace(microsecond=1), source="openweather", weather="晴")
        response = self.client.get("/api/environment/dashboard-summary/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["weather_observations"], 2)
        self.assertEqual(data["air_quality_observations"], 1)
        self.assertEqual(data["status"], "available")

    def test_read_only_observation_lists_filter_and_paginate(self):
        now = datetime.now(timezone.utc)
        EnvironmentObservation.objects.create(city="北京市", observed_at=now, source="openweather", temperature=20, weather="晴", aqi=60, quality="Moderate", pm25=18)
        EnvironmentObservation.objects.create(city="兰州市", observed_at=now.replace(microsecond=1), source="openweather", humidity=40)
        weather = self.client.get("/api/environment/weather-observations/", {"city": "北京", "page_size": 1})
        air = self.client.get("/api/environment/air-quality-observations/", {"quality": "Moderate", "min_aqi": 50})
        self.assertEqual(weather.status_code, 200)
        self.assertEqual(weather.json()["total"], 1)
        self.assertIn("temperature", weather.json()["results"][0])
        self.assertEqual(air.status_code, 200)
        self.assertEqual(air.json()["total"], 1)
        self.assertEqual(air.json()["results"][0]["city"], "北京市")

    def test_analysis_uses_real_observations_and_marks_sparse_correlation(self):
        now = datetime.now(timezone.utc)
        EnvironmentObservation.objects.create(city="北京市", observed_at=now, source="openweather", aqi=50, quality="Good", pm25=10, pm10=20, temperature=18, weather="晴")
        EnvironmentObservation.objects.create(city="兰州市", observed_at=now.replace(microsecond=1), source="openweather", aqi=80, quality="Moderate", pm25=20, pm10=35, humidity=40)
        response = self.client.get("/api/environment/analysis-visualization/")
        self.assertEqual(response.status_code, 200)
        analyses = response.json()["analyses"]
        self.assertEqual(len(analyses), 5)
        self.assertGreater(len(analyses[0]["charts"][0]["rows"]), 0)
        correlation = next(chart for chart in analyses[4]["charts"] if chart["key"] == "part22")
        self.assertEqual(correlation["status"], "insufficient_data")

    def test_time_analysis_uses_indicator_timestamp_contract_and_monthly_averages(self):
        september = datetime(2026, 9, 1, 8, tzinfo=timezone.utc)
        october = datetime(2026, 10, 1, 8, tzinfo=timezone.utc)
        EnvironmentObservation.objects.create(city="北京市", observed_at=october, source="openweather", aqi=90, pm25=30, pm10=40)
        EnvironmentObservation.objects.create(city="北京市", observed_at=september, source="openweather", aqi=50, pm25=None, pm10=20)
        charts = self.client.get("/api/environment/analysis-visualization/").json()["analyses"][1]["charts"]
        aqi = next(chart for chart in charts if chart["key"] == "part6")
        pm25 = next(chart for chart in charts if chart["key"] == "part7")
        monthly = next(chart for chart in charts if chart["key"] == "part9")
        self.assertEqual([row["name"] for row in aqi["rows"]], ["AQI|2026-09-01T08:00:00+00:00", "AQI|2026-10-01T08:00:00+00:00"])
        self.assertEqual(len(pm25["rows"]), 1)
        self.assertEqual(monthly["rows"], [{"name": "2026-09", "value": 50.0}, {"name": "2026-10", "value": 90.0}])

    @patch("apps.accounts.environment.get_provider", side_effect=ProviderError("Provider unavailable"))
    def test_stale_cache_is_explicitly_marked(self, _provider):
        cache.set("北京市", {"city": "北京市", "observed_at": "2026-01-01T00:00:00+00:00", "source": "fake"})
        cache._data["北京市"]["stored_at"] = 0
        response = self.client.get("/api/environment/realtime/", {"city": "北京"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["data_status"], "stale_cache")
