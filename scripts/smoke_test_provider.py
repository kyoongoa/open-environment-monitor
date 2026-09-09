"""Optional local check for a real configured provider; never prints the API key."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
django.setup()

from apps.accounts.environment import ProviderError, get_provider  # noqa: E402

if not os.getenv("OPENWEATHER_API_KEY"):
    print("OPENWEATHER_API_KEY is not set; smoke test skipped.")
    raise SystemExit(2)

city = sys.argv[1] if len(sys.argv) > 1 else "Beijing"
try:
    data = get_provider().fetch_current(city)
except ProviderError as exc:
    print(f"Provider smoke test failed: {exc}")
    raise SystemExit(1)

required = ("city", "observed_at", "source", "pm25", "pm10", "temperature", "humidity", "weather")
missing = [field for field in required if data.get(field) is None]
if missing:
    print(f"Provider response is missing required fields: {', '.join(missing)}")
    raise SystemExit(1)
print(f"Provider OK: {data['source']} | {data['city']} | observed_at={data['observed_at']} | pm25={data['pm25']}")
