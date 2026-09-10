from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .environment import CityResolutionError, ProviderError, analysis_visualization, dashboard_summary, get_realtime, history, observation_page, resolve_city


@require_GET
def dashboard_summary_view(request):
    return JsonResponse({"data": dashboard_summary()})


@require_GET
def analysis_visualization_view(request):
    return JsonResponse(analysis_visualization())


def _observation_list_response(request, kind):
    try:
        page = max(int(request.GET.get("page", 1)), 1)
        page_size = min(max(int(request.GET.get("page_size", 20)), 1), 100)
        min_aqi = request.GET.get("min_aqi")
        max_aqi = request.GET.get("max_aqi")
        return JsonResponse(observation_page(kind, page=page, page_size=page_size, city=request.GET.get("city", "").strip(), start_date=request.GET.get("start_date", "").strip(), end_date=request.GET.get("end_date", "").strip(), quality=request.GET.get("quality", "").strip(), min_aqi=int(min_aqi) if min_aqi else None, max_aqi=int(max_aqi) if max_aqi else None))
    except ValueError:
        return JsonResponse({"error": {"code": "invalid_request", "message": "Pagination and AQI filters must be integers."}}, status=400)


@require_GET
def weather_observations_view(request):
    return _observation_list_response(request, "weather")


@require_GET
def air_quality_observations_view(request):
    return _observation_list_response(request, "air")


@require_GET
def realtime_view(request):
    try:
        return JsonResponse({"data": get_realtime(request.GET.get("city"))})
    except CityResolutionError as exc:
        return JsonResponse({"error": {"code": "invalid_city", "message": str(exc)}}, status=400)
    except ProviderError as exc:
        return JsonResponse({"error": {"code": "environment_unavailable", "message": str(exc)}}, status=503)


@require_GET
def history_view(request):
    try:
        city = resolve_city(request.GET.get("city"))
    except CityResolutionError as exc:
        return JsonResponse({"error": {"code": "invalid_city", "message": str(exc)}}, status=400)
    try:
        limit = min(max(int(request.GET.get("limit", 100)), 1), 500)
    except ValueError:
        return JsonResponse({"error": {"code": "invalid_request", "message": "limit must be an integer."}}, status=400)
    return JsonResponse({"data": history(city, limit)})


@require_GET
def trend_view(request):
    try:
        city = resolve_city(request.GET.get("city"))
    except CityResolutionError as exc:
        return JsonResponse({"error": {"code": "invalid_city", "message": str(exc)}}, status=400)
    return JsonResponse({"data": list(reversed(history(city, 48)))})
