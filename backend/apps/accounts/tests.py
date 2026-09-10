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

    @patch("apps.accounts.environment.get_provider", side_effect=ProviderError("Provider unavailable"))
    def test_stale_cache_is_explicitly_marked(self, _provider):
        cache.set("北京市", {"city": "北京市", "observed_at": "2026-01-01T00:00:00+00:00", "source": "fake"})
        cache._data["北京市"]["stored_at"] = 0
        response = self.client.get("/api/environment/realtime/", {"city": "北京"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["data_status"], "stale_cache")
