# Environment API

All responses are JSON. Real-time calls are intentionally unavailable (`503`) until `OPENWEATHER_API_KEY` is configured.

## `GET /api/environment/realtime/?city=北京`

Fetches current weather and pollutant concentrations through the configured provider. A successful provider response is validated, stored in the in-memory cache, and upserted into `accounts_environmentobservation`.

Example success fields: `city`, `observed_at`, `collected_at`, `source`, `aqi`, `quality`, `pm25`, `pm10`, `so2`, `no2`, `co`, `o3`, `temperature`, `humidity`, `wind_speed`, `weather`, and `data_status` (`live`, `cached`, or `stale_cache`). `aqi` is US AQI calculated only from PM2.5; it must not be treated as a local official composite AQI.

Example unavailable response (`503`):

```json
{"error":{"code":"environment_unavailable","message":"Environment API is not configured. Please configure OPENWEATHER_API_KEY."}}
```

## `GET /api/environment/history/?city=北京&limit=100`

Returns up to 500 persisted observations for a city, newest first. It never calls a provider.

## `GET /api/environment/trend/?city=北京`

Returns the latest 48 persisted observations in chronological order for charts. It never invents missing points; a newly configured installation has an empty trend until it collects observations.
