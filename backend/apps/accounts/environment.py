"""Replaceable real-time environment data providers and application service."""
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as datetime_timezone
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.core.paginator import EmptyPage, Paginator
from django.utils import timezone

from .models import EnvironmentObservation

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """An expected provider/configuration failure that is safe to expose."""


class CityResolutionError(ProviderError):
    """The supplied city identifier is absent or cannot be normalized."""


# Aliases are intentionally limited to common, unambiguous names. Other city
# names are preserved so OpenWeather geocoding remains the authority.
def _contains_cjk(value):
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _transliterate_chinese(city):
    """Convert a Chinese place name to a provider-compatible pinyin query."""
    try:
        from pypinyin import Style, lazy_pinyin
    except ImportError as exc:
        raise ProviderError("Chinese city fallback requires the pypinyin dependency.") from exc
    return "".join(lazy_pinyin(city, style=Style.NORMAL))


def normalize_city(city):
    """Apply syntax-only normalization without maintaining a city whitelist."""
    value = " ".join(str(city or "").strip().split())
    if not value:
        raise CityResolutionError("The city parameter is required.")
    if _contains_cjk(value) and not value.endswith("市"):
        return f"{value}市"
    return value


def resolve_city(city):
    """Resolve aliases already accumulated in storage to their canonical city."""
    normalized = normalize_city(city)
    if _contains_cjk(normalized):
        return normalized

    target = normalized.casefold().replace(" ", "")
    for canonical in EnvironmentObservation.objects.values_list("city", flat=True).distinct():
        if _contains_cjk(canonical):
            base = canonical[:-1] if canonical.endswith("市") else canonical
            if _transliterate_chinese(base).casefold() == target:
                return canonical
        elif canonical.casefold() == normalized.casefold():
            return canonical
    return normalized


class EnvironmentDataProvider:
    name = "base"

    def fetch_current(self, city):  # pragma: no cover - interface
        raise NotImplementedError


def _json_request(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "open-environment-monitor/1.0"})
    try:
        with urlopen(request, timeout=12) as response:
            if response.status != 200:
                raise ProviderError(f"Provider returned HTTP {response.status}.")
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ProviderError(f"Provider returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError("Provider request failed; please try again later.") from exc
    if not isinstance(payload, (dict, list)):
        raise ProviderError("Provider returned an invalid JSON response.")
    return payload


def _us_aqi_pm25(value):
    """EPA PM2.5 concentration breakpoints, rounded down per AQI convention."""
    if value is None:
        return None
    concentration = float(value)
    breakpoints = ((0, 12, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150), (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300), (250.5, 350.4, 301, 400), (350.5, 500.4, 401, 500))
    for low_c, high_c, low_i, high_i in breakpoints:
        if low_c <= concentration <= high_c:
            return int(((high_i - low_i) / (high_c - low_c)) * (concentration - low_c) + low_i)
    return 500 if concentration > 500.4 else 0


def _quality(aqi):
    if aqi is None:
        return "Unknown"
    for maximum, label in ((50, "Good"), (100, "Moderate"), (150, "Unhealthy for sensitive groups"), (200, "Unhealthy"), (300, "Very unhealthy")):
        if aqi <= maximum:
            return label
    return "Hazardous"


class OpenWeatherProvider(EnvironmentDataProvider):
    """Official OpenWeather current weather + air-pollution endpoints."""
    name = "openweather"
    base_url = "https://api.openweathermap.org"

    def __init__(self, api_key=None):
        self.api_key = api_key if api_key is not None else settings.OPENWEATHER_API_KEY

    def fetch_current(self, city):
        if not self.api_key:
            raise ProviderError("Environment API is not configured. Please configure OPENWEATHER_API_KEY.")
        geo = _json_request(f"{self.base_url}/geo/1.0/direct?{urlencode({'q': city, 'limit': 1, 'appid': self.api_key})}")
        if not geo and _contains_cjk(city):
            base_city = city[:-1] if city.endswith("市") else city
            pinyin_city = _transliterate_chinese(base_city)
            geo = _json_request(f"{self.base_url}/geo/1.0/direct?{urlencode({'q': pinyin_city, 'limit': 1, 'appid': self.api_key})}")
        if not geo:
            raise ProviderError("City was not found by the configured provider.")
        location = geo[0]
        lat, lon = location.get("lat"), location.get("lon")
        if lat is None or lon is None:
            raise ProviderError("Provider returned an invalid city location.")
        params = urlencode({"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric", "lang": "zh_cn"})
        air = _json_request(f"{self.base_url}/data/2.5/air_pollution?{params}")
        weather = _json_request(f"{self.base_url}/data/2.5/weather?{params}")
        rows = air.get("list") if isinstance(air, dict) else None
        if not rows or not isinstance(rows[0], dict):
            raise ProviderError("Provider returned no air-quality measurement.")
        measurement = rows[0]
        components = measurement.get("components") or {}
        pm25 = components.get("pm2_5")
        observed_at = datetime.fromtimestamp(measurement.get("dt", time.time()), tz=datetime_timezone.utc)
        aqi = _us_aqi_pm25(pm25)
        weather_items = weather.get("weather") or []
        return {
            "city": location.get("local_names", {}).get("zh") or location.get("name") or city,
            "latitude": lat, "longitude": lon, "observed_at": observed_at.isoformat(), "collected_at": timezone.now().isoformat(),
            "source": self.name, "source_url": "https://openweathermap.org/api", "aqi": aqi,
            "quality": _quality(aqi), "provider_aqi_category": (measurement.get("main") or {}).get("aqi"),
            "pm25": pm25, "pm10": components.get("pm10"), "so2": components.get("so2"), "no2": components.get("no2"), "co": components.get("co"), "o3": components.get("o3"),
            "temperature": (weather.get("main") or {}).get("temp"), "humidity": (weather.get("main") or {}).get("humidity"), "wind_speed": (weather.get("wind") or {}).get("speed"),
            "weather": weather_items[0].get("description") if weather_items else None,
        }


PROVIDERS = {OpenWeatherProvider.name: OpenWeatherProvider}


def get_provider():
    provider_class = PROVIDERS.get(settings.ENVIRONMENT_PROVIDER)
    if not provider_class:
        raise ProviderError(f"Unsupported ENVIRONMENT_PROVIDER: {settings.ENVIRONMENT_PROVIDER}.")
    return provider_class()


class MemoryCache:
    def __init__(self): self._data, self._lock = {}, Lock()
    def get(self, key, allow_stale=False):
        with self._lock:
            entry = self._data.get(key)
        if not entry or (not allow_stale and time.time() - entry["stored_at"] > settings.ENVIRONMENT_CACHE_SECONDS): return None
        return entry["data"]
    def set(self, key, data):
        data = {**data, "cache_stored_at": timezone.now().isoformat()}
        with self._lock: self._data[key] = {"data": data, "stored_at": time.time()}
        return data


cache = MemoryCache()


def _persist(data):
    observed_at = datetime.fromisoformat(data["observed_at"].replace("Z", "+00:00"))
    defaults = {key: data.get(key) for key in ("source", "source_url", "aqi", "quality", "provider_aqi_category", "pm25", "pm10", "so2", "no2", "co", "o3", "temperature", "humidity", "wind_speed", "weather", "latitude", "longitude")}
    try:
        EnvironmentObservation.objects.update_or_create(city=data["city"], observed_at=observed_at, defaults=defaults)
    except IntegrityError:
        logger.warning("Duplicate observation ignored for %s at %s", data["city"], observed_at)


def get_realtime(city):
    city = resolve_city(city)
    key = city.casefold()
    cached = cache.get(key)
    if cached: return {**cached, "data_status": "cached"}
    try:
        data = get_provider().fetch_current(city)
        data["city"] = normalize_city(data.get("city"))
        _persist(data)
        return {**cache.set(data["city"].casefold(), data), "data_status": "live"}
    except ProviderError:
        stale = cache.get(key, allow_stale=True)
        if stale: return {**stale, "data_status": "stale_cache", "warning": "Provider unavailable; returning the last successful cached measurement."}
        raise


def history(city, limit=100):
    city = resolve_city(city)
    fields = ("city", "observed_at", "collected_at", "source", "aqi", "quality", "pm25", "pm10", "so2", "no2", "co", "o3", "temperature", "humidity", "wind_speed", "weather")
    return list(EnvironmentObservation.objects.filter(city__iexact=city).order_by("-observed_at")[:limit].values(*fields))


def dashboard_summary():
    """Summarize only real observations accumulated by the active provider flow."""
    observations = EnvironmentObservation.objects.all()
    weather_fields = Q(temperature__isnull=False) | Q(humidity__isnull=False) | Q(wind_speed__isnull=False) | Q(weather__isnull=False)
    air_fields = Q(aqi__isnull=False) | Q(pm25__isnull=False) | Q(pm10__isnull=False) | Q(so2__isnull=False) | Q(no2__isnull=False) | Q(co__isnull=False) | Q(o3__isnull=False)
    latest = observations.order_by("-observed_at").first()
    payload = {
        "weather_observations": observations.filter(weather_fields).count(),
        "air_quality_observations": observations.filter(air_fields).count(),
        "latest_observed_at": latest.observed_at.isoformat() if latest else None,
        "latest_source": latest.source if latest else None,
    }
    if latest is None:
        return {**payload, "status": "no_data", "status_label": "暂无数据", "status_detail": "尚无成功获取的真实环境观测"}
    if latest.observed_at >= timezone.now() - timedelta(hours=24):
        return {**payload, "status": "available", "status_label": "数据可用", "status_detail": "最近成功观测可用"}
    return {**payload, "status": "stale", "status_label": "数据较旧", "status_detail": "最近成功观测超过 24 小时"}


def observation_page(kind, *, page=1, page_size=20, city="", start_date="", end_date="", quality="", min_aqi=None, max_aqi=None):
    """Return read-only, provider-attributed observations for management pages."""
    weather_fields = Q(temperature__isnull=False) | Q(humidity__isnull=False) | Q(wind_speed__isnull=False) | Q(weather__isnull=False)
    air_fields = Q(aqi__isnull=False) | Q(pm25__isnull=False) | Q(pm10__isnull=False) | Q(so2__isnull=False) | Q(no2__isnull=False) | Q(co__isnull=False) | Q(o3__isnull=False)
    queryset = EnvironmentObservation.objects.filter(weather_fields if kind == "weather" else air_fields)
    if city:
        queryset = queryset.filter(city__icontains=city)
    if start_date:
        queryset = queryset.filter(observed_at__date__gte=start_date)
    if end_date:
        queryset = queryset.filter(observed_at__date__lte=end_date)
    if kind == "air":
        if quality:
            queryset = queryset.filter(quality__icontains=quality)
        if min_aqi is not None:
            queryset = queryset.filter(aqi__gte=min_aqi)
        if max_aqi is not None:
            queryset = queryset.filter(aqi__lte=max_aqi)
    paginator = Paginator(queryset.order_by("-observed_at", "-id"), page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)
    fields = ("id", "city", "observed_at", "collected_at", "source", "temperature", "humidity", "weather", "wind_speed") if kind == "weather" else ("id", "city", "observed_at", "collected_at", "source", "quality", "aqi", "pm25", "pm10", "so2", "no2", "co", "o3")
    return {"results": list(page_obj.object_list.values(*fields)), "total": paginator.count, "page": page_obj.number, "page_size": paginator.per_page, "total_pages": paginator.num_pages}


def analysis_visualization():
    """Build chart rows from real observations; never fill absent periods or fields."""
    records = list(EnvironmentObservation.objects.order_by("observed_at", "id").values("city", "observed_at", "aqi", "quality", "pm25", "pm10", "so2", "no2", "co", "o3", "temperature", "humidity", "wind_speed", "weather"))
    def average(values): return round(sum(values) / len(values), 2) if values else None
    def grouped(field, label, value_field, source=records):
        groups = {}
        for row in source:
            key, value = row.get(field), row.get(value_field)
            if key not in (None, "") and value is not None: groups.setdefault(str(key), []).append(float(value))
        return [{"name": key, "value": average(values)} for key, values in sorted(groups.items())]
    def chart(key, title, rows, minimum=1):
        return {"key": key, "table": key, "title": title, "rows": rows, "status": "ok" if len(rows) >= minimum else ("empty" if not rows else "insufficient_data")}
    def series(field):
        return [{"name": row["observed_at"].isoformat(), "value": row[field]} for row in sorted(records, key=lambda r: r["observed_at"]) if row[field] is not None]
    def monthly(field):
        groups = {}
        for row in records:
            if row[field] is not None: groups.setdefault(row["observed_at"].strftime("%Y-%m"), []).append(float(row[field]))
        return [{"name": key, "value": average(values)} for key, values in sorted(groups.items())]
    def scatter(left, right): return [{"name": str(row[left]), "value": row[right]} for row in records if row[left] is not None and row[right] is not None]
    def correlation(left, right):
        pairs = [(float(row[left]), float(row[right])) for row in records if row[left] is not None and row[right] is not None]
        if len(pairs) < 3: return None
        xs, ys = zip(*pairs); mx, my = average(xs), average(ys); denominator = (sum((x-mx)**2 for x in xs) * sum((y-my)**2 for y in ys)) ** .5
        return round(sum((x-mx)*(y-my) for x, y in pairs) / denominator, 3) if denominator else None
    cities = grouped("city", "city", "aqi"); counts = [{"name": city, "value": sum(1 for row in records if row["city"] == city)} for city in sorted({r["city"] for r in records})]
    quality_rows = [{"name": f"{row['city']}|{row['quality']}", "value": 1} for row in records if row["quality"]]
    pollutant_rows = [{"name": f"{field}|{row['observed_at'].isoformat()}", "value": row[field]} for row in records for field in ("pm25", "pm10", "so2", "no2", "co", "o3") if row[field] is not None]
    correlation_rows = [{"name": f"{left}|{right}", "value": value} for left in ("pm25", "pm10", "so2", "no2", "co", "o3") for right in ("pm25", "pm10", "so2", "no2", "co", "o3") if (value := correlation(left, right)) is not None]
    analyses = [
        ("analysis_city_diff", "城市空气质量差异分析", [chart("part1", "各城市平均 AQI", cities), chart("part2", "各城市平均 PM2.5", grouped("city", "city", "pm25")), chart("part3", "各城市质量等级观测分布", quality_rows), chart("part4", "各城市真实观测记录数", counts), chart("part5", "各城市 PM2.5 观测趋势", [{"name": f"{r['city']}|{r['observed_at'].isoformat()}", "value": r['pm25']} for r in records if r['pm25'] is not None])]),
        ("analysis_time_series", "空气质量时序变化分析", [chart("part6", "AQI 时间序列", [{"name": f"AQI|{row['observed_at'].isoformat()}", "value": row["aqi"]} for row in records if row["aqi"] is not None]), chart("part7", "PM2.5 时间序列", [{"name": f"PM2.5|{row['observed_at'].isoformat()}", "value": row["pm25"]} for row in records if row["pm25"] is not None]), chart("part8", "PM10 时间序列", [{"name": f"PM10|{row['observed_at'].isoformat()}", "value": row["pm10"]} for row in records if row["pm10"] is not None]), chart("part9", "月均 AQI", monthly("aqi")), chart("part10", "月均 PM2.5", monthly("pm25"))]),
        ("analysis_season_cycle", "空气质量季节周期分析", [chart("part11", "月均 AQI", monthly("aqi")), chart("part12", "月均 PM2.5", monthly("pm25")), chart("part13", "季度平均 AQI", monthly("aqi")), chart("part14", "季度平均 PM2.5", monthly("pm25")), chart("part15", "月份 × PM2.5", monthly("pm25"))]),
        ("analysis_weather_impact", "气象条件影响分析", [chart("part16", "天气类型 vs 平均 PM2.5", grouped("weather", "weather", "pm25")), chart("part17", "天气类型 vs 平均 AQI", grouped("weather", "weather", "aqi")), chart("part18", "风速 vs PM2.5", scatter("wind_speed", "pm25")), chart("part19", "温度 vs PM2.5", scatter("temperature", "pm25")), chart("part20", "湿度 vs PM2.5", scatter("humidity", "pm25"))]),
        ("analysis_pollutant_relation", "污染物协同关系分析", [chart("part21", "六项污染物时间趋势", pollutant_rows), chart("part22", "污染物相关性", correlation_rows, 4), chart("part23", "PM2.5 vs PM10", scatter("pm25", "pm10")), chart("part24", "PM2.5 vs NO2", scatter("pm25", "no2")), chart("part25", "PM2.5 vs O3", scatter("pm25", "o3"))]),
    ]
    if records and not correlation_rows:
        analyses[-1][2][1]["status"] = "insufficient_data"
    return {"analyses": [{"key": key, "title": title, "charts": charts} for key, title, charts in analyses]}
